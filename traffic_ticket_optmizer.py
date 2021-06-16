#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tuesday June 6th, 2021
@author: Corie Cox

OVERVIEW:
This module addresses the use case of determining the police ticketing policy
(speed threshhold, number of officers) for optimized ticket revenue. The
optimizer considers an overall traffic pattern (collection of driver profiles),
officer cost, and time to write a ticket. It balances ticketing revenue with the
opportunity cost of writing the ticket, and the percentage of target drivers
caught with the cost of adding another officer.

Run the file for a simulation of traffic under the optimal police ticketing policy!

CLASSES:
    DriverProfile: a profile representing all drivers who drive a certain mph over the speed limit
    Driver: represents an individual driver
    Cop: represents a cop
    Cops: represents a collection of cops
    TrafficPattern: a collection of DriverProfiles representing an overall traffic pattern
    
TODO:
    - optimize n_samples for performance when calculating p_driver_ticketed
    - pull in real data to fit assumptions to
    - fit officer ticketing time to a distribution and randomize
    - build out an officer scheduling feature that considers varying TrafficPatterns
      across hours of day and days of week
"""

from scipy.stats import expon
from random import random, choices
from functools import reduce
import time
from copy import deepcopy

INF = 999_999_999

class DriverProfile:
    """a profile representing all drivers who drive a certain mph over the speed limit"""
    def __init__(self, mph_over_limit=0, mins_between_drivers=INF):
        self.mph_over_limit = mph_over_limit
        self.mins_between_drivers = mins_between_drivers
        self.drivers_per_min = 1/mins_between_drivers
        self.dollars_ticketed = mph_over_limit * 10
        self.revenue_opportunity_per_hour = self.dollars_ticketed * self.drivers_per_min * 60

    def __str__(self):
        return f"{self.mph_over_limit}mph over"

    def __repr__(self):
        return self.__str__()

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

    # O(n*m) time where n is duration_mins, and m is self.drivers_per_min
    def get_driver_schedule(self, duration_mins=60):
        """returns a list of Driver times in minutes that are randomly spaced apart"""
        elapsed_mins, schedule = 0, []
        while elapsed_mins < duration_mins:
            elapsed_mins += expon.ppf(random()) * self.mins_between_drivers
            schedule.append(elapsed_mins)
        return schedule

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

class Cop():
    """represents a cop"""
    ticketing_time_mins = 15
    dollar_cost_per_hour = 300
    n_cops = 0
    
    def __init__(self):
        self.mins_until_avail = 0
        Cop.n_cops += 1
        self.id = Cop.n_cops
        
    def __str__(self):
        return f"(Cop_{self.id}, {round(self.mins_until_avail,1)} mins)" 
    
    def __repr__(self):
        return self.__str__()

class Cops():
    """represents a collection of cops"""
    p_driver_ticketed_cache = {}
    
    # O(n) time where n is n_cops
    def __init__(self, n_cops):
        if n_cops < 1:
            raise ValueError('must have at least one cop')
        self.queue = [Cop() for _ in range(n_cops)]
    
    def __str__(self):
        return f"{self.cops_queue}"
    
    def __iadd__(self, other: int):
        self.queue += [Cop() for _ in range(other)]
        return self
    
    def __isub__(self, other: int):
        if len(self.queue) - other < 1:
            raise ValueError('must have at least one cop')
        del self.queue[-other:]
        return self

    def is_available(self):
        return self.queue[0].mins_until_avail == 0
    
    def get_cost_per_hour(self):
        return Cop.dollar_cost_per_hour * len(self.queue)
    
    # O(n) time where n is n_cops
    def elapse_mins(self, mins):
        for cop in reversed(self.queue):
            if cop.mins_until_avail == 0:
                break
            cop.mins_until_avail = max(0, cop.mins_until_avail - mins)
    
    # O(1) assuming use of a linked list queue
    def issue_ticket(self, driver=None):
        ticketing_cop = self.queue[0]
        ticketing_cop.mins_until_avail = Cop.ticketing_time_mins
        self.queue.append(self.queue.pop(0))  
        if driver is not None:
            driver.got_ticket = True
            driver.ticketing_cop = deepcopy(ticketing_cop)

    def p_driver_ticketed(self, mins_between_drivers, n_samples=10_000):
        """returns the probability a driver is ticketed"""
        
        # O(1)
        if len(self.queue) == 1:
            return mins_between_drivers / (mins_between_drivers + Cop.ticketing_time_mins)
        cache_key = f"{round(mins_between_drivers, 4)}_{len(self.queue)}"
        if cache_key in Cops.p_driver_ticketed_cache:
            return Cops.p_driver_ticketed_cache[cache_key]
        
        # O(n*m) where n is n_samples and m is n_cops
        n_drivers, n_drivers_ticketed = 0, 0
        for i in range(n_samples):
            self.elapse_mins(expon.ppf(random()) * mins_between_drivers)
            if self.is_available():
                self.issue_ticket()
                n_drivers_ticketed += 1
            n_drivers += 1
        
        self.elapse_mins(INF)
        p_driver_ticketed = n_drivers_ticketed / n_drivers
        Cops.p_driver_ticketed_cache[cache_key] = p_driver_ticketed
        
        return n_drivers_ticketed / n_drivers  

class TrafficPattern:
    """a collection of DriverProfiles representing an overall traffic pattern"""
    
    # O(nlog(n)) time where n is len(driver_profiles)
    def __init__(self, driver_profiles):
        if len(driver_profiles) == 0:
            raise ValueError('no driver profiles provided')
        self.cops = Cops(1)
        self.driver_profiles = sorted(driver_profiles, key=lambda x: x.mph_over_limit, reverse=True)
        self.total_profile = reduce(lambda x, y: x + y, self.driver_profiles)
        self.profile_weights = [d.drivers_per_min/self.total_profile.drivers_per_min for d in self.driver_profiles]
        self.target_profiles = []
        self.target_profile = DriverProfile()

    # O(n) time where n is n_cops
    def get_revenue_per_hour(self):
        """returns the expected ticket revenue per hour"""
        tp = self.target_profile
        p_driver_ticketed = self.cops.p_driver_ticketed(tp.mins_between_drivers)
        return p_driver_ticketed * tp.revenue_opportunity_per_hour - self.cops.get_cost_per_hour()
    
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
            prev_target_profiles = self.target_profiles
            self.cops += 1
            self.optimize_on_target_profiles()
        self.cops -= 1
        self.target_profiles = prev_target_profiles
        self.target_profile = reduce(lambda x, y: x + y, self.target_profiles)
    
    # O(n*log(m)+n*k) time where n is len(schedule), m is len(driver_profiles) and k is n_cops
    def get_traffic_simulation(self, duration_mins):
        """returns a list of a random drivers following this traffic and ticketing pattern"""
        cops = self.cops
        schedule = self.total_profile.get_driver_schedule(duration_mins)        
        profiles = choices(population=self.driver_profiles, weights=self.profile_weights, k=len(schedule))
        drivers = [Driver(a, b) for (a,b) in zip(profiles,schedule)]

        prev_driver = Driver(DriverProfile(), 0)
        for driver in drivers:
            elapsed_mins = driver.scheduled_min - prev_driver.scheduled_min
            prev_driver = driver
            cops.elapse_mins(elapsed_mins)
            if driver.profile in self.target_profiles and cops.is_available():
                cops.issue_ticket(driver)
        
        cops.elapse_mins(INF)
        return drivers
    
    # O((n*log(m)) time n is len(schedule), and m is len(driver_profiles)
    def simulate_traffic(self, iter_secs=.3, duration_mins=600):
        """runs a simulation of the traffic and ticketing patterns"""
        drivers = self.get_traffic_simulation(duration_mins)
        driver = drivers.pop(0)
        for duration_min in range(duration_mins):
            print('\n')
            time.sleep(iter_secs)
            
            while driver.scheduled_min < duration_min:
                minute = int(driver.scheduled_min)
                if driver.got_ticket:
                    ticket = driver.profile.dollars_ticketed
                    print(f"{minute}min: {driver.profile} - ticketed ${ticket} by {driver.ticketing_cop}")
                    time.sleep(iter_secs*5)
                else:
                    print(f"{minute}min: {driver.profile}")
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
    cops, mins_between_drivers  = trafficPattern.cops, trafficPattern.target_profile.mins_between_drivers
    p_ticketed = cops.p_driver_ticketed(mins_between_drivers) * 100
    print(f"the max expected hourly ticket revenue of ${max_revenue} occurs when ticketing the top {n_profiles} speed group(s) using {len(cops.queue)} cop(s). This will ticket {round(p_ticketed)}% of target drivers")
    
    time.sleep(3)
    trafficPattern.simulate_traffic()
