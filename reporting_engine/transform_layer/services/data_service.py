from pandas.core.frame import DataFrame
import dateutil.parser as parser
import pandas as pd
from django.db import connections


from transform_layer.services.utils import date_str_to_int, get_control_query

import copy
import time

SCOPE_HIERARCHY = "hierarchy"
SCOPE_GEOGRAPHY = "geography"

#1 instance of DataService for 1 scope
class DataService:

    def __init__(self, scope):
        self._fact_services = None
        self._service_types = None
        self._family_services = None
        self._new_familiy_services = None
        #[monthly, weekly, daily] skeletons 
        self._date_skeletons = None

        self.scope_type = scope["scope_type"]
        self.control_query = get_control_query(scope["control_type_name"])
        self.scope_field = scope["scope_field"]
        self.scope_value = scope["scope_field_value"]
        self.start_date = date_str_to_int(scope["startDate"])
        self.end_date = date_str_to_int(scope["endDate"])

    ## returns DataFrame for a specific data definition
    def get_data_for_definition(self, id):
        if id>=1 and id <= 22:
            if(self._fact_services) is None:
                self._fact_services = self.__get_fact_services()
            return self._fact_services
        elif id <= 25:
            if(self._service_types) is None:
                self._service_types = self.__get_service_types()
            return self._service_types
        elif id <= 31:
            if(self._family_services) is None:
                self._family_services = self.__get_family_services()
            return self._family_services
        elif id <= 56:
            #used same base data for new families(32-46) and geographies(47-56)
            if(self._new_familiy_services) is None:
                self._new_familiy_services = self.__get_new_family_services()
            return self._new_familiy_services
        elif id <= 68:
            
            if(self._new_familiy_services) is None:
                self._new_familiy_services = self.__get_new_family_services()
            if(self._date_skeletons) is None:
                self._date_skeletons = self.__get_date_skeletons()
            
            #list[0] = services
            #list[1] = families
            #list[2] = members
            #list[3] = monthly_date_skeleton
            #list[4] = weekly_date_skeleton
            #list[5] = daily_date_skeleton
            return self._new_familiy_services + self._date_skeletons

           



        ## retrieves fact_services
    def __get_fact_services(self):
        conn = connections['source_db']

        table1 = ""
        left1 = right1 = ""

        if self.scope_type  == "hierarchy":
            table1 = "dim_hierarchies"
            left1 = right1 = "hierarchy_id"
        elif self.scope_type  == "geography":
            table1 = "dim_geos"
            left1 = "dimgeo_id"
            right1 = "id"

        query = f"""
        SELECT
            fs.research_service_key,
            fs.{left1},
            fs.service_status,
            fs.service_id,
            fs.research_family_key,
            fs.served_children,
            fs.served_adults,
            fs.served_seniors,
            fs.served_total,
            fsm.research_member_key
        FROM 
            fact_services AS fs
            INNER JOIN dim_service_types ON fs.service_id = dim_service_types.id
            LEFT JOIN {table1} AS t1 ON fs.{left1} = t1.{right1}
            LEFT JOIN dim_service_statuses ON fs.service_status = dim_service_statuses.status 
            LEFT JOIN fact_service_members AS fsm ON fs.research_service_key = fsm.research_service_key
        WHERE
            fs.service_status = 17
            {self.control_query}
            AND t1.{self.scope_field} = {self.scope_value}
            AND fs.date >= {self.start_date} AND fs.date <= {self.end_date}
        """
        start_time = time.time()
        result = pd.read_sql(query, conn)
        print(str(time.time() - start_time), ' seconds to download fact services')
        mem_usage = result.memory_usage(deep=True).sum() 
        print(str(mem_usage), 'bytes for fact services')
        return result


    def __get_service_types(self):
        conn = connections['source_db']

        extra_join = ""
        if self.scope_type == "hierarchy":
            table1 = "dim_hierarchies"
            left1 = right1 = "hierarchy_id"
        elif self.scope_type == "geography":
            table1 = "dim_geos"
            left1 = "dimgeo_id"
            right1 = "id"
            extra_join = """INNER JOIN dim_hierarchies ON fact_services.hierarchy_id = dim_hierarchies.loc_id"""


        query = f"""
        SELECT
            fact_services.research_service_key,
            fact_services.research_family_key,
            fact_services.service_id,
            dim_service_types.name AS service_name,
            dim_service_types.service_category_code,
            dim_service_types.service_category_name,
            fact_services.served_total,
            dim_hierarchies.loc_id
        FROM
            fact_services
            INNER JOIN dim_service_types ON fact_services.service_id = dim_service_types.id
            INNER JOIN {table1} ON fact_services.{left1} = {table1}.{right1}
            {extra_join if self.scope_type == "geography" else ""}
        WHERE
            fact_services.service_status = 17 
            {self.control_query}
            AND fact_services.date >= {self.start_date} AND fact_services.date <= {self.end_date}
            AND {table1}.{self.scope_field} = {self.scope_value}
        """
        start_time = time.time()
        result = pd.read_sql(query, conn) 
        print(str(time.time() - start_time), ' seconds to download service types')
        mem_usage = result.memory_usage(deep=True).sum() 
        print(str(mem_usage), 'bytes for service types')
        return result


    def __get_family_services(self):
        conn = connections['source_db']

        table1 = ""
        left1 = right1 = ""

        if self.scope_type == "hierarchy":
            table1 = "dim_hierarchies"
            left1 = right1 = "hierarchy_id"
        elif self.scope_type == "geography":
            table1 = "dim_geos"
            left1 = "dimgeo_id"
            right1 = "id"

        query = f"""
        SELECT
            fact_services.research_family_key,
            COUNT(fact_services.research_service_key) AS num_services,
            AVG(fact_services.served_total) AS avg_fam_size,
            SUM(fact_services.is_first_service_date) as timeframe_has_first_service_date,
            AVG(fact_services.days_since_first_service) AS avg_days_since_first_service,
            MAX(fact_services.days_since_first_service) AS max_days_since_first_service,
            dim_family_compositions.family_composition_type
        FROM 
            fact_services
            INNER JOIN dim_families ON fact_services.research_family_key = dim_families.research_family_key
            INNER JOIN dim_family_compositions ON dim_families.family_composition_type = dim_family_compositions.id
            INNER JOIN dim_service_types ON fact_services.service_id = dim_service_types.id
            INNER JOIN {table1}  ON fact_services.{left1} = {table1}.{right1}
        WHERE
            fact_services.service_status = 17 
            {self.control_query}
            AND fact_services.date >= {self.start_date} AND fact_services.date <= {self.end_date}
            AND {table1}.{self.scope_field} = {self.scope_value}
        GROUP BY
            fact_services.research_family_key,
            dim_family_compositions.family_composition_type
        """
        start_time = time.time()
        result = pd.read_sql(query, conn)
        print(str(time.time() - start_time), ' seconds to download family services')
        mem_usage = result.memory_usage(deep=True).sum() 
        print(str(mem_usage), 'bytes for family services')
        return result

    def __get_new_family_services(self):
        conn = connections['source_db']

        if self.scope_type == "hierarchy":
            table1 = "dim_hierarchies"
            left1 = right1 = "hierarchy_id"
        elif self.scope_type == "geography":
            table1 = "dim_geos"
            left1 = "dimgeo_id"
            right1 = "id"

        services_query = f"""
        SELECT
            fs.research_service_key,
            fs.research_family_key,
            fs.service_id,
            fs.hierarchy_id,
            dim_hierarchies.event_id,
            dim_hierarchies.loc_id,
            dim_geos_event.fips_cnty AS fips_cnty_event,
            dim_service_types.name as service_name,
            dim_service_types.service_category_code,
            dim_service_types.service_category_name,
            fs.served_total,
            fs.is_first_service_date,
            fs.served_children,
            fs.served_adults,
            fs.served_seniors,
            fs.family_composition_type,
            dim_geos.lattitude AS latitude_fs,
            dim_geos.longitude AS longitude_fs,
            dim_geos.fips_cnty AS fips_cnty_fs,
            fs.dummy_trip,
            fs.distance_miles,
            fs.direction,
            fs.date,
            dim_dates.calendaryearmonth AS calendaryearmonth,
            dim_dates.sunyearweek       AS sunyearweek,
            dim_dates.dayofweek         AS dayofweek,
            dim_hierarchy_events.name  AS event_name
        FROM
            fact_services AS fs
            INNER JOIN dim_service_types ON fs.service_id = dim_service_types.id
            INNER JOIN dim_hierarchies ON fs.hierarchy_id = dim_hierarchies.hierarchy_id
            INNER JOIN dim_dates ON fs.date = dim_dates.date_key
            INNER JOIN dim_hierarchy_events ON dim_hierarchies.event_id = dim_hierarchy_events.id
            LEFT JOIN dim_geos ON fs.dimgeo_id = dim_geos.id
            LEFT JOIN dim_geos AS dim_geos_event ON dim_hierarchy_events.dimgeo_id = dim_geos_event.id
        WHERE
            fs.service_status = 17 
            {self.control_query}
            AND fs.date >= {self.start_date} AND fs.date <= {self.end_date}
            AND {table1}.{self.scope_field} = {self.scope_value}
        """

        families_query = f"""
            SELECT
                fs.research_family_key,
                COUNT( fs.research_service_key ) AS num_services,
                AVG( fs.served_total ) AS avg_fam_size,
                SUM( fs.is_first_service_date ) AS timeframe_has_first_service_date,
                AVG( fs.days_since_first_service ) AS avg_days_since_first_service,
                MAX( fs.days_since_first_service ) AS max_days_since_first_service,
                dim_family_compositions.family_composition_type,
                dim_families.datekey_first_service,
                dim_families.dummy_use_geo,
                dim_families.latitude_5,
                dim_families.longitude_5,
                dim_families.dimgeo_id,
                dim_geos.fips_state,
                dim_geos.fips_cnty,
                dim_geos.fips_zcta
            FROM
                fact_services AS fs
                INNER JOIN dim_families ON fs.research_family_key = dim_families.research_family_key
                INNER JOIN dim_family_compositions ON dim_families.family_composition_type = dim_family_compositions.id
                INNER JOIN dim_service_types ON fs.service_id = dim_service_types.id
                INNER JOIN dim_dates ON fs.date = dim_dates.date_key
                INNER JOIN {table1} AS t1 ON fs.{left1} = t1.{right1}
                LEFT JOIN dim_geos ON dim_families.dimgeo_id = dim_geos.id
            WHERE
                fs.service_status = 17
                {self.control_query}
                AND fs.date >= {self.start_date} AND fs.date <= {self.end_date}
                AND t1.{self.scope_field} = {self.scope_value}
            GROUP BY
                fs.research_family_key,
                dim_family_compositions.family_composition_type,
                dim_families.datekey_first_service,
                dim_families.dummy_use_geo,
                dim_families.latitude_5,
                dim_families.longitude_5,
                dim_families.dimgeo_id,
                dim_geos.fips_state,
                dim_geos.fips_cnty,
                dim_geos.fips_zcta
        """

        members_query = f"""
        SELECT
            fs_mem.research_member_key,
            dim_members.research_family_key, 
            COUNT( fs.research_service_key ) AS num_services,
            SUM( fs_mem.is_first_service_date ) AS timeframe_has_first_service_date,
            AVG( fs_mem.days_since_first_service ) AS avg_days_since_first_service,
            MAX( fs_mem.days_since_first_service ) AS max_days_since_first_service,
            dim_members.datekey_first_served,
            dim_members.gender,
            dim_members.current_age,
            dim_members.race_id,
            dim_members.ethnic_id,
            dim_members.immigrant_id,
            dim_members.language_id,
            dim_members.disability_id,
            dim_members.military_id,
            dim_members.healthcare_id,
            dim_members.education_id,
            dim_members.employment_id,
            dim_families.datekey_first_service AS dim_families_datekey_first_service,
            SUM( fs.is_first_service_date ) AS dim_families_timeframe_has_first_service_date,
            dim_geos.fips_state,
            dim_geos.fips_cnty,
            dim_geos.fips_zcta
        FROM
            fact_services AS fs
            INNER JOIN dim_service_types ON fs.service_id = dim_service_types.id
            INNER JOIN {table1} AS t1 ON fs.{left1} = t1.{right1}
            INNER JOIN dim_dates ON fs.date = dim_dates.date_key
            INNER JOIN fact_service_members AS fs_mem ON fs.research_service_key = fs_mem.research_service_key
            INNER JOIN dim_members ON fs_mem.research_member_key = dim_members.research_member_key
            INNER JOIN dim_families ON dim_members.research_family_key = dim_families.research_family_key
            LEFT JOIN dim_geos ON dim_families.dimgeo_id = dim_geos.id
        WHERE
            fs.service_status = 17
            {self.control_query}
            AND t1.{self.scope_field} = {self.scope_value}
            AND fs.date >= {self.start_date} AND fs.date <= {self.end_date}
        GROUP BY
            fs_mem.research_member_key
        """
        
        print("Services Query:")
        print(services_query)
        print("Families Query:")
        print(families_query)
        print("Members Query")
        print(members_query)

        start_time = time.time()
        services = pd.read_sql(services_query, conn)
        families = pd.read_sql(families_query, conn)
        members = pd.read_sql(members_query, conn)
        print(str(time.time() - start_time), ' seconds to download new family services')
        mem_usage = services.memory_usage(deep=True).sum() + families.memory_usage(deep=True).sum() + members.memory_usage(deep=True).sum()
        print(str(mem_usage), 'bytes for new family services')

        

        return [services, families, members]

    def __get_monthly_date_skeleton(self):
        conn = connections['source_db']

        query_skeleton_month = f""" 
        SELECT
            dim_dates.CalendarYearMonth as calendaryearmonth,
            MIN(dim_dates.FullDate) as calendaryearmonth_start,
            CONCAT(dim_dates.MonthName, ' - ', dim_dates.CalendarYear) as calendaryearmonth_name
        FROM 
            dim_dates
        WHERE
            dim_dates.date_key >= {self.start_date} AND dim_dates.date_key <= {self.end_date}
        GROUP BY dim_dates.CalendarYearMonth
        """
        
        start_time = time.time()
        skeleton = pd.read_sql(query_skeleton_month, conn)
        print(str(time.time() - start_time), ' seconds to download monthly date skeleton')
        mem_usage = skeleton.memory_usage(deep=True).sum() 
        print(str(mem_usage), 'bytes for monthly date skeleton')

        return skeleton

    def __get_weekly_date_skeleton(self):
        conn = connections['source_db']

        query_skeleton_week = f"""
        SELECT 
            dim_dates.SunYearWeek AS sunyearweek, 
            MIN(dim_dates.date_key) as sunyearweek_start 
        FROM 
            dim_dates 
        WHERE
            dim_dates.date_key >= {self.start_date} 
            AND dim_dates.date_key <= {self.end_date}
        GROUP BY 
            dim_dates.SunYearWeek
        """

        start_time = time.time()
        skeleton = pd.read_sql(query_skeleton_week, conn)
        print(str(time.time() - start_time), ' seconds to download weekly date skeleton')
        mem_usage = skeleton.memory_usage(deep=True).sum() 
        print(str(mem_usage), 'bytes for weekly date skeleton')

        return skeleton

    def __get_daily_date_skeleton(self):
        conn = connections['source_db']

        query_skeleton_day = f"""
        SELECT 
            dim_dates.date_key as date,
            dim_dates.FullDate as date_label 
        FROM dim_dates
        WHERE
            dim_dates.date_key >= {self.start_date} 
            AND dim_dates.date_key <= {self.end_date}
        """

        start_time = time.time()
        skeleton = pd.read_sql(query_skeleton_day, conn)
        print(str(time.time() - start_time), ' seconds to download daily date skeleton')
        mem_usage = skeleton.memory_usage(deep=True).sum() 
        print(str(mem_usage), 'bytes for daily date skeleton')

        return skeleton

    def __get_date_skeletons(self):
        monthly = self.__get_monthly_date_skeleton()
        weekly = self.__get_weekly_date_skeleton()
        daily = self.__get_daily_date_skeleton()

        return [monthly, weekly, daily]