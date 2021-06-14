#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tuesday June 6th, 2021

@author: Corie Cox

OVERVIEW:
This module addresses the use case of police ticking policy (spped threshhold,
number of officers) optimzied on ticket revenue. The optimizer considers an
overall traffic pattern (collection of driver profiles), officer cost, and
time to write a ticket. It balances ticketing revenue with the opportunity cost
of writing the ticket, and percentage of target drivers caught with the cost of
adding another officer.

CLASSES:
    DriverProfile: a driver profile defined by number of miles per hour over the speed limit
    Driver: represents an individual driver
    Cop: repretsents a cop
    TrafficPattern: a collection of DriverProfiles representing an overall traffic pattern
    
TODO:
    - optimize n_samples for performance when calculating p_driver_ticketed
"""

from scipy.stats import expon
from random import random, choices
from functools import reduce
import time

INF = 999_999_999

class DriverProfile:
    """a driver profile unique by the number of miles per hour driven over the speed limit"""
    def __init__(self, mph_over_limit=0, mins_between_drivers=INF):
        self.mph_over_limit = mph_over_limit
        self.mins_between_drivers = mins_between_drivers
        self.drivers_per_min = 1/mins_between_drivers
        self.dollars_ticketed = mph_over_limit * 10
        self.revenue_opportunity_per_hour = self.dollars_ticketed * self.drivers_per_min * 60

    # O(n*m) time where n is duration_mins, and m is self.drivers_per_min
    def get_driver_schedule(self, duration_mins=60):
        """returns a list of Driver times in minutes that are randomly spaced apart"""
        elapsed_mins, schedule = 0, []
        while elapsed_mins < duration_mins:
            elapsed_mins += expon.ppf(random()) * self.mins_between_drivers
            schedule.append(elapsed_mins)
        return schedule

    def __str__(self):
        return f"{self.mph_over_limit}mph over"

    # O(1) time
    def __add__(self, other):
        new_profile = DriverProfile()
        new_profile.drivers_per_min = self.drivers_per_min + other.drivers_per_min
        new_profile.mins_between_drivers = 1 / new_profile.drivers_per_min
        new_profile.revenue_opportunity_per_hour = self.revenue_opportunity_per_hour + other.revenue_opportunity_per_hour
        
        self_weight = self.drivers_per_min / new_profile.drivers_per_min
        other_weight = other.drivers_per_min / new_profile.drivers_per_min
        new_profile.dollars_ticketed = self_weight * self.dollars_ticketed + other_weight * other.dollars_ticketed
        new_profile.mph_over_limit = self_weight * self.mph_over_limit + other_weight * other.mph_over_limit
        
        return new_profile

class Driver:
    """represents an individual driver"""
    def __init__(self, driverProfile, scheduled_min):
        self.profile = driverProfile
        self.scheduled_min = scheduled_min
        self.got_ticket = False
        self.ticketing_cop = None
    
    def __str__(self):
        mph_over = self.profile.mph_over_limit
        scheduled_min = round(self.scheduled_min, 2)
        return f"{mph_over}mph over at minute: {scheduled_min}" 

class Cop:
    """represents a cop"""
    ticketing_time_mins=15
    dollar_cost_per_hour = 300
    n_cops = 0
    p_driver_ticketed_cache = {}
    
    def __init__(self):
        Cop.n_cops += 1
        self.id = Cop.n_cops 
        self.mins_until_available = 0
    
    def __str__(self):
        return f"Cop_{self.id}"
    
    def is_available(self):
        return self.mins_until_available == 0
    
    @classmethod
    def p_driver_ticketed(cls, mins_between_drivers, n_cops=1, n_samples=10_000):
        """returns the probability a driver is ticketed"""
        
        # O(1)
        if n_cops == 1:
            return mins_between_drivers / (mins_between_drivers + cls.ticketing_time_mins)
        cache_key = f"{round(mins_between_drivers, 4)}_{n_cops}"
        if cache_key in cls.p_driver_ticketed_cache:
            return cls.p_driver_ticketed_cache[cache_key]
        
        # O(n*m) where n is n_samples and m is n_cops
        cops = [Cop() for _ in range(n_cops)]
        n_drivers, n_drivers_ticketed = 0, 0
        for i in range(n_samples):
            
            elasped_mins = expon.ppf(random()) * mins_between_drivers
            for cop in reversed(cops):
                if cop.mins_until_available == 0:
                    break
                cop.mins_until_available = max(0, cop.mins_until_available-elasped_mins)
    
            if cops[0].is_available():
                cops[0].mins_until_available = Cop.ticketing_time_mins
                cops += [cops.pop(0)]
                n_drivers_ticketed += 1
            n_drivers += 1
        
        p_driver_ticketed = n_drivers_ticketed / n_drivers
        cls.p_driver_ticketed_cache[cache_key] = p_driver_ticketed
        return n_drivers_ticketed / n_drivers  
        

class TrafficPattern:
    """a collection of DriverProfiles representing an overall traffic pattern"""
    
    # O(nlog(n)) time where n is len(driver_profiles)
    def __init__(self, driver_profiles):
        if len(driver_profiles) == 0:
            raise ValueError('no driver profiles provided')
        self.n_cops = 1
        self.driver_profiles = sorted(driver_profiles, key=lambda x: x.mph_over_limit, reverse=True)
        self.total_profile = reduce(lambda x, y: x + y, self.driver_profiles)
        self.profile_weights = [d.drivers_per_min/self.total_profile.drivers_per_min for d in self.driver_profiles]
        self.target_profiles = []
        self.target_profile = DriverProfile()

    # O(n) time where n is n_cops
    def get_revenue_per_hour(self):
        """returns the expected ticket revenue per hour"""
        tp = self.target_profile
        p_driver_ticketed = Cop.p_driver_ticketed(tp.mins_between_drivers, self.n_cops)
        return p_driver_ticketed * tp.revenue_opportunity_per_hour - self.n_cops * Cop.dollar_cost_per_hour
    
    # O(n) time where n is len(driver_profiles)
    def optimize_on_target_profiles(self):
        """updates target_profiles to the revenue maximizing set"""
        max_revenue = -INF
        while self.get_revenue_per_hour() > max_revenue and len(self.target_profiles) < len(self.driver_profiles):
            max_revenue = self.get_revenue_per_hour()
            marginal_profile = self.driver_profiles[len(self.target_profiles)]
            self.target_profiles.append(marginal_profile)
            self.target_profile += marginal_profile
        if self.get_revenue_per_hour() < max_revenue:
            self.target_profiles.pop()
            self.target_profile = reduce(lambda x, y: x + y, self.target_profiles)
        
    # O(n*m) where n is len(driver_profiles) and m is max(n_cops)
    def optimize_on_n_cops(self):
        """updates n_cops, target_profiles to the revenue maximizing set"""
        self.optimize_on_target_profiles()
        max_revenue = -INF
        while self.get_revenue_per_hour() >= max_revenue:
            max_revenue = self.get_revenue_per_hour()
            self.n_cops += 1
            self.optimize_on_target_profiles()
        self.n_cops -= 1
    
    # O(n*log(m)+n*k) time where n is len(schedule), m is len(driver_profiles) and k is n_cops
    def get_traffic_simulation(self, duration_mins):
        """returns a list of a random drivers following this traffic and ticketing pattern"""
        schedule = self.total_profile.get_driver_schedule(duration_mins)        
        profiles = choices(population=self.driver_profiles, weights=self.profile_weights, k=len(schedule))
        drivers = [Driver(a, b) for (a,b) in zip(profiles,schedule)]

        cops = [Cop() for _ in range(n_cops)]
        prev_driver = Driver(DriverProfile(), 0)
        for driver in drivers:
            
            elasped_mins = driver.scheduled_min - prev_driver.scheduled_min
            prev_driver = driver
            for cop in reversed(cops):
                if cop.mins_until_available == 0:
                    break
                cop.mins_until_available = max(0, cop.mins_until_available-elasped_mins)
            
            if driver.profile in self.target_profiles and cops[0].is_available():
                driver.got_ticket = True
                driver.ticketing_cop = cops[0]
                cops[0].mins_until_available = Cop.ticketing_time_mins
                cops += [cops.pop(0)]
        
        return drivers
    
    # O((n*log(m)) time n is len(schedule), and m is len(driver_profiles)
    def simulate_traffic(self, iter_secs=.3, duration_mins=600):
        """runs a simulation of the traffic and ticketing patterns"""
        drivers = self.get_traffic_simulation(duration_mins)
        driver = drivers.pop(0)
        for duration_min in range(duration_mins):
            time.sleep(iter_secs)
            print('\n')
            while driver.scheduled_min < duration_min:
                if driver.got_ticket:
                    ticket = driver.profile.dollars_ticketed
                    minute = int(driver.scheduled_min)
                    print(f"{driver.profile} (ticketed ${ticket} at minute {minute}) by {driver.ticketing_cop}")
                    time.sleep(iter_secs*5)
                else:
                    print(driver.profile)
                driver = drivers.pop(0)

if __name__ == "__main__":    
    trafficPattern = TrafficPattern([ # mph_over_limit | mins_between_drivers
        DriverProfile(5, 5),
        DriverProfile(10, 10),
        DriverProfile(15, 20),
        DriverProfile(20, 40),
    ])
    trafficPattern.optimize_on_n_cops()
    
    max_revenue = round(trafficPattern.get_revenue_per_hour(), 2)
    n_profiles = len(trafficPattern.target_profiles)
    n_cops = trafficPattern.n_cops
    p_ticketed = Cop.p_driver_ticketed(trafficPattern.target_profile.mins_between_drivers, n_cops) * 100
    print(f"the max expected hourly ticket revenue of ${max_revenue} occurs when ticketing the top {n_profiles} speed group(s) using {n_cops} cops. This will ticket {round(p_ticketed)}% of target drivers")
    
    time.sleep(3)
    trafficPattern.simulate_traffic()
