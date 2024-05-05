from ortools.sat.python import cp_model

import models
from models import Schedule, Employee


class ScheduleSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print solutions."""

    def __init__(self, shifts, employees: [Employee], schedule: Schedule, limit):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._shifts = shifts
        self._employees = employees
        self._schedule = schedule
        self._solution_count = 0
        self._solution_limit = limit
        self.best_solution = {}
        self.best_difference = 100000000

    def on_solution_callback(self):
        self._solution_count += 1
        filled_schedule = {}
        # print(f"Solution {self._solution_count}")
        for d in self._schedule.days:
            # print(f"Day {self._schedule.days[d]}")
            for s in self._schedule.shifts:
                if self._schedule.schedule[d][s]:
                    if self._schedule.schedule_requirements[d][s] != 0:
                        # (f"\t Shift starting at {self._schedule.shifts[s]} needs {self._schedule.schedule_requirements[d][s]} workers and is staffed by: ")
                        for i, e in enumerate(self._employees):
                            if d in e.days_available and s in e.hours_available and self.value(self._shifts[(i, d, s)]):
                                try:
                                    filled_schedule[d][s].append(i)
                                except KeyError:
                                    try:
                                        filled_schedule[d][s] = [i]
                                    except KeyError:
                                        filled_schedule[d] = {s: [i]}
                                # print(f"\t\t{e.name}")
        if len(self._schedule.filled_schedule) == 0:
            self._schedule.filled_schedule = filled_schedule
            self.stop_search()
        else:
            diff, _, _ = models.compare_schedules(self._schedule.filled_schedule, filled_schedule)
            if diff < self.best_difference:
                self.best_solution = filled_schedule
                self.best_difference = diff

        if self._solution_count >= self._solution_limit:
            print(f"Stop search after {self._solution_limit} solutions. Best solution is {self.best_difference} changes.")
            self._schedule.save_schedule_to_file("../data/best_new_sched.csv", self.best_solution)
            self.stop_search()

    def solution_count(self):
        return self._solution_count
