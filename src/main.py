from ortools.sat.python import cp_model

import models
from models import Schedule, Employee
from solution_printer import ScheduleSolutionPrinter


def set_hours(schedule: Schedule):
    schedule.set_schedule("W", "9am", False)
    schedule.set_schedule("Th", "11am", False)

    schedule.set_schedule("Su", "6am", False)
    schedule.set_schedule("Su", "4pm", False)
    schedule.set_schedule("Su", "5pm", False)
    schedule.set_schedule("Su", "6pm", False)

    schedule.set_schedule("S", "6am", False)
    schedule.set_schedule("S", "4pm", False)
    schedule.set_schedule("S", "5pm", False)
    schedule.set_schedule("S", "6pm", False)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    current_schedule_file_name = "../data/saved_sched.csv"

    model = cp_model.CpModel()

    employees = []
    # load employees from file
    with open("../data/employees.csv") as f:
        headers = f.readline()
        for line in f:
            name, shifts, days_worked, start_time, end_time = line.replace(" ", "").replace("\n", "").split(',')
            days_worked = [x for x in days_worked.split('.')]
            employees.append(Employee(name, int(shifts), days_worked, start_time, end_time))

    employee_dict = {e.name: i for i, e in enumerate(employees)}

    sched = Schedule(employee_dict=employee_dict, employees=employees)
    # set hours that don't need scheduling
    set_hours(sched)

    # Calculate shift distribution
    base_requirement = 2
    for d in sched.days:
        shifts_in_day = [i for i, j in enumerate(sched.schedule[d]) if j is True]
        number_of_shifts = sum(e.shifts_per_day for e in employees if d in e.days_available)
        surplus_shifts = number_of_shifts - (base_requirement * len(shifts_in_day))

        extra_people_desired = {k: sched.shift_distribution[k] * surplus_shifts for k in sched.shift_distribution}
        for s in shifts_in_day:
            sched.set_personnel_requirement_int(day=d,
                                                shift=s,
                                                number_of_people=base_requirement + int(extra_people_desired[s]))
            surplus_shifts -= int(extra_people_desired[s])
            extra_people_desired[s] -= int(extra_people_desired[s])

        extra_people_desired = [(extra_people_desired[k], k) for k in extra_people_desired]
        extra_people_desired.sort(reverse=True)
        for p, shift in extra_people_desired:
            # print(sched.schedule_requirements[d])
            if surplus_shifts <= 0:
                break
            sched.increment_personnel_requirement_int(day=d, shift=shift, number_of_people=1)
            surplus_shifts -= 1

        """print(sched.schedule_requirements[d])
        print(f"{sched.days[d]} has {len(shifts_in_day)}"
              f" shifts and {number_of_shifts} available"
              f" worker shifts, {number_of_shifts - (len(shifts_in_day) * base_requirement)} surplus.")
        print(f"{sched.days[d]} has {sum(sched.schedule_requirements[d])} shifts assigned")
        print(f"{sched.days[d]} shifts: {sched.schedule_requirements[d]}")"""

    # Build constraints
    shifts = {}
    for i, e in enumerate(employees):
        for d in e.days_available:  # d is the day worked
            for s in e.hours_available:  # s is the hour available
                shifts[(i, d, s)] = model.new_bool_var(f"shift_e{i}_d{d}_s{s}")

    # add exactly one shift per phone/product employee and two for insurance employees
    for i, e in enumerate(employees):
        if e.shifts_per_day == 1:
            for d in e.days_available:
                # print(f"{e.name} must work a shift on {sched.days[d]}")
                model.add_exactly_one(shifts[(i, d, s)] for s in e.hours_available)
        else:
            for d in e.days_available:
                shifts_worked_in_day = []
                # print(f"{e.name} must work {e.shifts_per_day} shifts on {sched.days[d]}")
                for s in e.hours_available:
                    shifts_worked_in_day.append(shifts[(i, d, s)])
                model.add(sum(shifts_worked_in_day) == e.shifts_per_day)

    # insurance employees cannot work sequential shifts
    for i, e in enumerate(employees):
        if e.shifts_per_day > 1:
            for d in e.days_available:
                for s in e.hours_available:
                    if s + 1 in e.hours_available:
                        # print(f"{e.name} cannot work both {sched.shifts[s]} and {sched.shifts[s+1]} on {sched.days[d]}")
                        model.add(sum([shifts[i, d, s], shifts[i, d, s + 1]]) <= 1)

    # fulfill shift requirements
    for d in sched.days:
        for s in sched.shifts:
            workers_in_shift = []
            for e in [i for i, e in enumerate(employees) if d in e.days_available and s in e.hours_available]:
                workers_in_shift.append(shifts[(e, d, s)])
            model.add(sum(workers_in_shift) == sched.schedule_requirements[d][s])

    # add requested time off
    with open("../data/shifts_off.csv") as f:
        headers = f.readline()
        for line in f:
            employee_name, day_off, shift_off = line.replace(" ", "").replace("\n", "").split(',')
            day = sched.inverted_days[day_off]
            shift = sched.inverted_shifts[shift_off]
            employee_index = employee_dict[employee_name]
            model.add(sum([shifts[(employee_index, day, shift)]]) == 0)

    # Load current solution if exists

    solver = cp_model.CpSolver()
    solver.parameters.linearization_level = 0
    # Enumerate all solutions.
    solver.parameters.enumerate_all_solutions = True

    saved_sched = sched.load_schedule_from_file(current_schedule_file_name)
    sched.assign_schedule_from_dict(saved_sched)

    solution_limit = 1000
    solution_printer = ScheduleSolutionPrinter(
        shifts, employees=employees, schedule=sched, limit=solution_limit
    )

    solver.solve(model, solution_printer)

    # Statistics.
    print("\nStatistics")
    print(f"  - conflicts      : {solver.num_conflicts}")
    print(f"  - branches       : {solver.num_branches}")
    print(f"  - wall time      : {solver.wall_time} s")
    print(f"  - solutions found: {solution_printer.solution_count()}")

    new_sched = sched.load_schedule_from_file("../data/best_new_sched.csv")
    num_diff, added_shifts, removed_shifts = models.compare_schedules(saved_sched, new_sched)

    print(f"\nBetween the old shift and new we have {num_diff} differences.\n")

    print("\nShifts to remove:")
    for day, shift, removed_staff in removed_shifts:
        print(f"{sched.days[day]}: {sched.shifts[shift]}: {','.join([sched.employees[r].name for r in removed_staff])}")

    print("\nShifts to add:")
    for day, shift, added_staff in added_shifts:
        print(f"{sched.days[day]}: {sched.shifts[shift]}: {','.join([sched.employees[a].name for a in added_staff])}")


