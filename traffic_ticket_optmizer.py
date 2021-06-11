#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tuesday June 6th, 2021

@author: Corie Cox


OVERVIEW:
This module addresses the use case of a police officer deciding which types of
speeders (mph over the speed limit) to pull over with the objective of maximizing
ticket revenue. It considers the different types of speeders along with the average
amount of time a booking takes.

TODO:
    - build in assumptions around mins_between_speeders fitting a poisson distrubtion.
      this will allow us to make variance assumptions and construct simulations.
    - refactor get_max_ticket_revenue_per_hour into an O(n) operation to improve
      performance on large amounts of speeder_types. this can be done by replacing
      get_ticket_revenue_per_hour() with a constant time fuction that adjusts
      ticket_revenue_per_hour as number of speeder_types increment.
      NOTE: this may not be needed if amount of speeder_types is expected to remain small.
"""

from copy import deepcopy

class SpeederType:
    """a type of speeder defined by mph_over_limit and mins_between_speeders"""
    def __init__(self, mph_over_limit, mins_between_speeders):
        self.mph_over_limit = mph_over_limit
        self.mins_between_speeders = mins_between_speeders
        self.dollars_fined = mph_over_limit * 10
        self.speeders_per_hour = 60/mins_between_speeders

class SpeederGroup:
    """a collection of speeder types wih functionality for evalating ticketing revenue"""
    
    def __init__(self):
        self.speeder_types = []

    def add_speeder_type(self, *args, **kwargs):
        self.speeder_types.append(SpeederType(*args, **kwargs))
    
    # O(n) time where n is len(speeder_types)
    def add_speeder_types(self, speeder_types):
            for args in speeder_types:
                self.add_speeder_type(*args)

    # O(n) time where n is len(self.speeder_types)
    def get_total_speeders_per_hour(self):
        """returns the expected number of speeders per hour across all speeder types"""
        return sum([s.speeders_per_hour for s in self.speeder_types])
    
    # O(n) time where n is len(self.speeder_types)
    def get_expected_ticket_value(self):
        """returns the expected ticket value of a randomly chosen speeder"""
        if len(self.speeder_types) == 0:
            return 0
        speeders_per_hour = self.get_total_speeders_per_hour()
        return sum([s.dollars_fined * s.speeders_per_hour/speeders_per_hour for s in self.speeder_types])    

    # O(n) time where n is len(self.speeder_types)
    def get_ticket_revenue_per_hour(self, booking_time_mins=15):
        """returns the expected ticket revenue per hour assuming all speeder types are stopped"""
        if len(self.speeder_types) == 0:
            return 0
        expected_mins_to_find_speeder = 1 / (self.get_total_speeders_per_hour() / 60)
        expected_stops_per_hour = 60 / (expected_mins_to_find_speeder + booking_time_mins) 
        expected_ticket_value = self.get_expected_ticket_value()
        return round(expected_stops_per_hour * expected_ticket_value, 2)
    
    # O(n^2) time where n is len(self.speeder_types)
    def get_max_ticket_revenue_per_hour(self, booking_time_mins=15):
        """returns the [max_ticket_revenue, max_speeder_type_count] when stopping a variable number or speeder types"""
        self.speeder_types.sort(key=lambda x: x.mph_over_limit)
        speederGroup = deepcopy(self)
        max_ticket_revunue, max_speeder_type_count = 0, len(self.speeder_types)
        for i in range(len(self.speeder_types)):
            speederGroup.speeder_types = self.speeder_types[i:]
            ticket_revenue = speederGroup.get_ticket_revenue_per_hour(booking_time_mins)
            if ticket_revenue > max_ticket_revunue:
                max_ticket_revunue = ticket_revenue
                max_speeder_type_count = len(self.speeder_types) - i
        return [max_ticket_revunue, max_speeder_type_count]

if __name__ == "__main__":
    booking_time_mins = 15
    speederGroup = SpeederGroup()
    speederGroup.add_speeder_types([ # mph_over_limit | mins_between_speeders
        [5, 5],
        [10, 10],
        [15, 20],
        [20, 40]
    ])
    opportunity = speederGroup.get_total_speeders_per_hour() * speederGroup.get_expected_ticket_value()
    print(f"expected total hourly revenue opportunity is ${opportunity}")
    revenue = speederGroup.get_ticket_revenue_per_hour(booking_time_mins)
    print(f"expected hourly revenue when booking all speed groups is ${revenue}")
    max_revenue = speederGroup.get_max_ticket_revenue_per_hour(booking_time_mins)
    print(f"the max expected hourly revenue of ${max_revenue[0]} occurs when booking the top {max_revenue[1]} speed group(s)") 
