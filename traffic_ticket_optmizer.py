#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tuesday June 6th, 2021

@author: Corie Cox


OVERVIEW:
This module addresses the use case of a police officer deciding which driver profiles
(mph over the speed limit) to pull over with the objective of maximizing ticket revenue.
It considers an overall traffic patter (collection of driver profiles) along with
the average amount of time a booking takes.

CLASSES:
    DriverProfile: a driver profile defined by number of miles per hour over the speed limit
    TrafficPattern: a collection of DriverProfile's'
"""

from scipy.stats import expon
from random import random, choices
import time

class DriverProfile:
    """a driver profile defined by number of miles per hour over the speed limit"""
    def __init__(self, mph_over_limit, mins_between_drivers):
        self.mph_over_limit = mph_over_limit
        self.mins_between_drivers = mins_between_drivers
        self.dollars_fined = mph_over_limit * 10
        self.expected_drivers_per_min = 1/mins_between_drivers
    
    # O(1) time
    def get_random_mins(self):
        """returns a simulated number of minutes before a driver of this profile is seen"""
        return expon.ppf(random()) * self.mins_between_drivers
    
    # (1) time
    @staticmethod
    def get_random_profile(profile_weights):
        """returns a simulated ticket value from a collection of ticket weights"""
        mph_over = list(profile_weights.keys())
        weights = list(profile_weights.values())
        random_mph_over = choices(population=mph_over, weights=weights)[0]
        profile = DriverProfile(random_mph_over, 1)
        return profile
    
    # O(1) time
    def get_expected_revenue_per_hour(self, booking_time_mins=15):
        """returns the expected ticket revenue per hour subject to a booking time"""
        stops_per_hour = 60 * 1 / (self.mins_between_drivers + booking_time_mins)
        return round(stops_per_hour * self.dollars_fined, 2)

    # O(1) time
    def __add__(self, other):
        new_profile = DriverProfile(0, 1)
        new_profile.expected_drivers_per_min = self.expected_drivers_per_min + other.expected_drivers_per_min
        new_profile.mins_between_drivers = 1 / new_profile.expected_drivers_per_min
        
        self_weight = self.expected_drivers_per_min / new_profile.expected_drivers_per_min
        other_weight = other.expected_drivers_per_min / new_profile.expected_drivers_per_min
        new_profile.dollars_fined = self_weight * self.dollars_fined + other_weight * other.dollars_fined
        new_profile.mph_over_limit = self_weight * self.mph_over_limit + other_weight * other.mph_over_limit
        
        return new_profile


class TrafficPattern:
    """a collection of DriverProfile's representing an overall traffic pattern"""
    
    # O(n) time where n is len(driver_profiles)
    def __init__(self, driver_profiles):
        if len(driver_profiles) == 0:
            raise ValueError('no driver profiles provided')
        self.driver_profiles = [DriverProfile(*args) for args in driver_profiles]
        self.total_profile = self.get_total_profile()
        total_drivers_per_min = sum([d.expected_drivers_per_min for d in self.driver_profiles])
        self.ticket_weights = {d.mph_over_limit:d.expected_drivers_per_min/total_drivers_per_min for d in self.driver_profiles}
    
    # O(n) time where n is len(driver_profiles)
    def get_total_profile(self):
        """returns a single driver profile representing the collective driver profiles"""
        total_profile = self.driver_profiles[0]
        for i in range(1, len(self.driver_profiles)):
            total_profile += self.driver_profiles[i]
        return total_profile
    
    # O(n) time where n is len(self.driver_profiles)
    def get_max_revenue_per_hour(self, booking_time_mins=15):
        """returns the [max_revenue, max_driver_profies] when booking optimal driver profiles"""
        self.driver_profiles.sort(key=lambda x: x.mph_over_limit,reverse=True)
        cur_profile = self.driver_profiles[0]
        max_revunue = cur_profile.get_expected_revenue_per_hour(booking_time_mins)
        max_driver_profiles = 1
        for i in range(1, len(self.driver_profiles)):
            cur_profile += self.driver_profiles[i]
            cur_revunue = cur_profile.get_expected_revenue_per_hour(booking_time_mins)
            if cur_revunue > max_revunue:
                max_revunue = cur_revunue
                max_driver_profiles = i + 1 
        return [max_revunue, max_driver_profiles]
    
    def simulate_traffic(self, realtime_scale=30, n_mins=60, speed_tolerance=5, booking_time_mins=15):
        """prints out a simlation of speeders and tickets"""
        mins_elapsed, cop_mins_left_boking = 0, 0
        while mins_elapsed < n_mins:
            random_mins = self.total_profile.get_random_mins()
            random_profile = DriverProfile.get_random_profile(self.ticket_weights)
            mins_elapsed += random_mins
            time.sleep(random_mins * 1/realtime_scale * 60)
            if random_profile.mph_over_limit <= speed_tolerance or cop_mins_left_boking > 0:
                cop_mins_left_boking = max([0, cop_mins_left_boking-random_mins])
                print(random_profile.mph_over_limit)
                continue
            cop_mins_left_boking = booking_time_mins
            print(f"{random_profile.mph_over_limit} (ticketed ${random_profile.dollars_fined})")

if __name__ == "__main__":
    booking_time_mins = 15
    trafficPattern = TrafficPattern([ # mph_over_limit | mins_between_drivers
        [5, 5],
        [10, 10],
        [15, 20],
        [20, 40]
    ])
    max_revenue = trafficPattern.get_max_revenue_per_hour(booking_time_mins)
    print(f"the max expected hourly revenue of ${max_revenue[0]} occurs when booking the top {max_revenue[1]} speed group(s)")
    trafficPattern.simulate_traffic()
