#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tuesday June 6th, 2021

@author: Corie Cox

OVERVIEW:
This module addresses the use case of a police officer deciding which driver profiles
(mph over the speed limit) to ticket with the objective of maximizing ticket revenue.
The optimizer considers an overall traffic pattern (collection of driver profiles)
along with the average amount of time a ticket takes to write. For each driver profile,
it balances ticketing revenue with the opportunity cost of writing the ticket.

CLASSES:
    DriverProfile: a driver profile defined by number of miles per hour over the speed limit
    Driver: represents an individual driver
    TrafficPattern: a collection of DriverProfiles representing an overall traffic pattern
"""

from scipy.stats import expon
from random import random, choices
import time

class DriverProfile:
    """a driver profile unique by the number of miles per hour driven over the speed limit"""
    def __init__(self, mph_over_limit, mins_between_drivers):
        self.mph_over_limit = mph_over_limit
        self.mins_between_drivers = mins_between_drivers
        self.drivers_per_min = 1/mins_between_drivers
        self.dollars_ticketed = mph_over_limit * 10

    # O(n*m) time where n is duration_mins, and m is self.drivers_per_min
    def get_traffic_gap_mins(self, duration_mins=0):
        """returns a list of random numbers representing minutes until the next driver"""
        if duration_mins == 0:
            return expon.ppf(random()) * self.mins_between_drivers
        elapsed_mins = 0
        
        mins_list = []
        while elapsed_mins < duration_mins:
            mins = expon.ppf(random()) * self.mins_between_drivers
            mins_list.append(mins)
            elapsed_mins += mins
        return mins_list

    def __str__(self):
        return f"{self.mph_over_limit}mph over"

    # O(1) time
    def __add__(self, other):
        new_profile = DriverProfile(0, 1)
        new_profile.drivers_per_min = self.drivers_per_min + other.drivers_per_min
        new_profile.mins_between_drivers = 1 / new_profile.drivers_per_min
        
        self_weight = self.drivers_per_min / new_profile.drivers_per_min
        other_weight = other.drivers_per_min / new_profile.drivers_per_min
        new_profile.dollars_ticketed = self_weight * self.dollars_ticketed + other_weight * other.dollars_ticketed
        new_profile.mph_over_limit = self_weight * self.mph_over_limit + other_weight * other.mph_over_limit
        
        return new_profile

class Driver:
    """represents an individual driver"""
    def __init__(self, driverProfile, traffic_gap_mins):
        self.profile = driverProfile
        self.traffic_gap_mins = traffic_gap_mins
    
    def __str__(self):
        mph_over = self.profile.mph_over_limit
        traffic_gap_mins = round(self.traffic_gap_mins, 2)
        return f"{mph_over}mph over, {traffic_gap_mins} mins behind previous car" 

class TrafficPattern:
    """a collection of DriverProfiles representing an overall traffic pattern"""
    
    # O(nlog(n)) time where n is len(driver_profiles)
    def __init__(self, driver_profiles, ticket_mins=15):
        if len(driver_profiles) == 0:
            raise ValueError('no driver profiles provided')
            
        self.driver_profiles = sorted(driver_profiles, key=lambda x: x.mph_over_limit, reverse=True)
        self.ticket_mins = ticket_mins
        self.total_profile = self.get_total_profile()
        self.profile_weights = [d.drivers_per_min/self.total_profile.drivers_per_min for d in self.driver_profiles]
    
    # O(n) time where n is len(driver_profiles)
    def get_total_profile(self):
        """returns a single DriverProfile representing the collective driver profiles"""
        total_profile = self.driver_profiles[0]
        for i in range(1, len(self.driver_profiles)):
            total_profile += self.driver_profiles[i]
        return total_profile

    # O(1) time
    def get_revenue_per_hour(self, driver_profile=None):
        """returns the expected ticket revenue per hour for the DriverProfile"""
        if driver_profile is None:
            driver_profile = self.total_profile
            
        total_ticket_mins = driver_profile.mins_between_drivers + self.ticket_mins
        tickets_per_hour = 60 * 1/total_ticket_mins
        return round(tickets_per_hour * driver_profile.dollars_ticketed, 2)             
    
    # O(n) time where n is len(self.driver_profiles)
    def get_target_profiles(self):
        """returns the revenue maximizing list of target DriverProfiles"""
        cur_profile = self.driver_profiles[0]
        target_profiles = [self.driver_profiles[0]]
        max_revenue = self.get_revenue_per_hour(cur_profile)
        for i in range(1, len(self.driver_profiles)):
            cur_profile += self.driver_profiles[i]
            cur_revenue = self.get_revenue_per_hour(cur_profile)
            if cur_revenue > max_revenue:
                target_profiles.append(self.driver_profiles[i])
                max_revenue = cur_revenue
        return target_profiles
    
    # O((k*n*log(m)) time where k is drivers_per_min, n is duration_mins, and m is len(driver_profiles)
    def get_drivers(self, duration_mins):
        """returns a list of random drivers to iterate through during simulations"""
        minutes = self.total_profile.get_traffic_gap_mins(duration_mins)        
        profiles = choices(population=self.driver_profiles, weights=self.profile_weights, k=len(minutes))
        return [Driver(a, b) for (a,b) in zip(profiles,minutes)]
    
    # O((k*n*log(m)) time where k is drivers_per_min, n is duration_mins, and m is len(driver_profiles)
    def simulate_traffic(self, target_profiles, realtime_scale=30, duration_mins=60):
        """runs a simlation of drivers with the target_profiles getting ticketed as resources allow"""
        drivers = self.get_drivers(duration_mins)
        remaining_ticket_mins = 0
        while drivers:
            driver = drivers.pop()
            time.sleep(driver.traffic_gap_mins * 1/realtime_scale * 60)
            if driver.profile in target_profiles and remaining_ticket_mins == 0:
                remaining_ticket_mins = self.ticket_mins
                print(f"{driver} (ticketed ${driver.profile.dollars_ticketed})")
            else:
                remaining_ticket_mins = max(0, remaining_ticket_mins - driver.traffic_gap_mins)
                print(driver)
                continue

if __name__ == "__main__":
    trafficPattern = TrafficPattern([ # mph_over_limit | mins_between_drivers
        DriverProfile(5, 5),
        DriverProfile(10, 10),
        DriverProfile(15, 20),
        DriverProfile(20, 40),
    ])
    target_profiles = trafficPattern.get_target_profiles()
    max_revenue = TrafficPattern(target_profiles).get_revenue_per_hour()
    print(f"the max expected hourly ticket revenue of ${max_revenue} occurs when ticketing the top {len(target_profiles)} speed group(s)")
    trafficPattern.simulate_traffic(target_profiles)
