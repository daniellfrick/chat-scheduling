def compare_schedules(old_sched: dict, new_sched: dict, print_differences=False):
    difference_count = 0
    added_shifts = []
    removed_shifts = []
    for d in Schedule.days:
        for s in Schedule.shifts:
            try:
                removed_staff = [e for e in old_sched[d][s] if e not in new_sched[d][s]]
                added_staff = [e for e in new_sched[d][s] if e not in old_sched[d][s]]
                difference_count += len(removed_staff)
                difference_count += len(added_staff)
                if len(removed_staff) > 0:
                    removed_shifts.append((d, s, removed_staff))
                if len(added_staff) > 0:
                    added_shifts.append((d, s, added_staff))
            except KeyError:
                pass

    # Count number of shifts that are different and return that number
    if print_differences:
        print(added_shifts)
        print(removed_shifts)
    return difference_count, added_shifts, removed_shifts


class Schedule:
    days = {
        0: "Su",  # "Sunday",
        1: "M",  # "Monday",
        2: "T",  # "Tuesday",
        3: "W",  # "Wednesday",
        4: "Th",  # "Thursday",
        5: "F",  # "Friday",
        6: "S",  # "Saturday"
    }

    # shift start time
    shifts = {
        0: "6am",
        1: "7am",
        2: "8am",
        3: "9am",
        4: "10am",
        5: "11am",
        6: "12pm",
        7: "1pm",
        8: "2pm",
        9: "3pm",
        10: "4pm",
        11: "5pm",
        12: "6pm"
    }

    # shift distribution
    shift_distribution = {
        0: 0.01612903226,
        1: 0.03225806452,
        2: 0.08064516129,
        3: 0.03225806452,
        4: 0.1451612903,
        5: 0.1129032258,
        6: 0.1774193548,
        7: 0.1290322581,
        8: 0.1290322581,
        9: 0.08064516129,
        10: 0.03225806452,
        11: 0.03225806452,
        12: 0.0
    }

    def __init__(self, employee_dict=None, employees=None):
        if employee_dict is None:
            employee_dict = {}
        self.schedule_requirements = [[0 for _ in range(len(self.shifts))] for _ in range(len(self.days))]
        self.schedule = [[True for _ in range(len(self.shifts))] for _ in range(len(self.days))]
        self.inverted_days = {self.days[k]: k for k in self.days}
        self.inverted_shifts = {self.shifts[k]: k for k in self.shifts}
        self.filled_schedule = {}
        self.employee_dict = employee_dict
        self.employees = employees

    def set_personnel_requirement(self, day: str, shift: str, number_of_people: int):
        self.schedule_requirements[self.inverted_days[day]][self.inverted_shifts[shift]] = number_of_people

    def set_personnel_requirement_int(self, day: int, shift: int, number_of_people: int):
        self.schedule_requirements[day][shift] = number_of_people

    def increment_personnel_requirement_int(self, day: int, shift: int, number_of_people: int):
        self.schedule_requirements[day][shift] += number_of_people

    def set_schedule(self, day: str, shift: str, shift_worked: bool):
        self.schedule[self.inverted_days[day]][self.inverted_shifts[shift]] = shift_worked

    def load_schedule_from_file(self, filename: str = "current_schedule.csv"):
        filled_schedule = {}
        try:
            with open(filename) as f:
                for line in f:
                    cells = line.replace('\n', '').split(',')
                    if cells[0] in self.days.values():
                        current_day = self.inverted_days[cells[0]]
                    elif cells[0] in self.shifts.values():
                        current_shift = self.inverted_shifts[cells[0]]
                        try:
                            filled_schedule[current_day][current_shift] = [self.employee_dict[e] for e in cells[1:] if e != '']
                        except KeyError:
                            filled_schedule[current_day] = {current_shift: [self.employee_dict[e] for e in cells[1:] if e != '']}
        except FileNotFoundError:
            pass
        return filled_schedule

    def assign_schedule_from_dict(self, filled_schedule):
        self.filled_schedule = filled_schedule

    def save_schedule_to_file(self, filename: str, sched: dict):
        with open(filename, "w") as f:
            for d in self.days:
                f.write(f"{self.days[d]}\n")
                for s in self.shifts:
                    try:
                        f.write(f"{self.shifts[s]},{','.join([self.employees[i].name for i in sched[d][s]])}\n")
                    except KeyError:
                        f.write(f"{self.shifts[s]}\n")


class Employee:
    def __init__(self, name: str, shifts_per_day: int, days_worked: [str], day_start: str, day_end: str):
        temp = Schedule()
        self.name = name
        self.shifts_per_day = shifts_per_day
        self.days_available = [temp.inverted_days[i] for i in days_worked]
        self.hours_available = range(temp.inverted_shifts[day_start], temp.inverted_shifts[day_end] + 1)
