from pandas.core.frame import DataFrame
import dateutil.parser as parser
import pandas as pd
import json

import transform_layer.calc_families as calc_families


# data def 32
def get_new_families(data: 'list[DataFrame]'):
    """Calculate number of new families DataDef 32

    Arguments:
    data - data frames to fulfill definiton id

    Modifies:
    Nothing

    Returns: added_members
    added_families - new family count
    """
    
    families = data[1]
    families = families[families['timeframe_has_first_service_date']>0]
    return len(families)

# data def 33
def get_new_members(data: 'list[DataFrame]'):
    """Calculate number of new members DataDef 33

    Arguments:
    data - data frames to fulfill definiton id

    Modifies:
    Nothing

    Returns: added_members
    added_members - json of new member count

    """
    members = data[2]
    members = members[members['timeframe_has_first_service_date']>0]
    return len(members)

# data def 34
def get_new_members_to_old_families(data: 'list[DataFrame]'):
    """Calculate number of people served DataDef 34

    Arguments:
    data - data frames to fulfill definiton id

    Modifies:
    Nothing

    Returns: added_members
    added_members - json of new members added to families that already have been served

    """
    members = data[2]
    members = members[members['timeframe_has_first_service_date']>0]
    members = members[members['dim_families_timeframe_has_first_service_date']>0]
    return len(members)

# data def 35
def get_services_to_new_families(data: 'list[DataFrame]'):
    families = data[1]
    families = families[families['timeframe_has_first_service_date']>0]
    return families['num_services'].sum()

#data def 36
def get_families_first_service(data: 'list[DataFrame]'):
    services = data[0]
    services = services[services['is_first_service_date']>0]
    return len(services)

# data def 37/38
def get_new_families_freq_visits(data: 'list[DataFrame]'):
        """Calculate frequency of visits for new families DataDef 37

        Arguments:
        data - data frames to fulfill definiton id

        Modifies:
        Nothing

        Returns: added_members
        added_members - json of number of services new families used

        """
        families = data[1]
        families = families[families['timeframe_has_first_service_date']>0]
        families = families.astype({'num_services': 'int64'})
        families = families.groupby(['num_services'])
        families = families.agg({'research_family_key': 'count', 'num_services': 'sum'})
        largeSum = families.iloc[24:].sum()
        families.at[25, 'research_family_key'] = largeSum.iloc[0]
        families.at[25, 'num_services'] = largeSum.iloc[1]
        families = families.rename(columns={'research_family_key' :'n_families', 'num_services':'sum_services'})
        families = families.head(25)
        return families.to_json()

# data def 39
def get_new_fam_household_composition(data: 'list[DataFrame]'):
    families = data[1]
    result_dict = {
        "adults_and_children":0,
        "adults_and_seniors":0,
        "adults_only":0,
        "adults_seniors_and_children":0,
        "children_and_seniors":0,
        "children_only":0,
        "seniors_only":0
    }

    for index, row in families.iterrows():
        result_dict[row["family_composition_type"]]+=1
    
    return json.dumps(result_dict)

# data def 40
def get_new_fam_composition_key_insight(data: 'list[DataFrame]'):
    families = data[1]

    result_dict = {
        "has_child_senior":0,
        "no_child_senior":0
    }

    for index, row in families.iterrows():
        if row["family_composition_type"] == "adults_only":
            result_dict["no_child_senior"]+=1
        else:
            result_dict["has_child_senior"]+=1

    return json.dumps(result_dict)

#data def 41
def get_new_fam_hh_size_dist_1_to_10(data):
    """Calculate household size distibutions for families of size 1 to 10 DataDef 41

    Arguments:
    data - data frames to fulfill definiton id

    Modifies:
    Nothing

    Returns: added_members
    num_new_families - new family distribution counts 1 to 10
    """

    families = data[1]
    families = families[families['timeframe_has_first_service_date'] > 0]
    return calc_families.get_household_size_distribution_1_to_10(families)

#data def 42
def get_new_fam_hh_size_dist_classic(data):
    families = data[1]
    families = families[families['timeframe_has_first_service_date'] > 0]
    return calc_families.get_household_size_distribution_classic(families)

#data def 43
def get_relationship_length_fam_mean(data):
    """Calculate mean length of relationship for families DataDef 43

    Arguments:
    data - data frames to fulfill definiton id

    Modifies:
    Nothing

    Returns: added_members
    mean_relationship_length - mean relationship length of families
    """

    families = data[1]
    return families['max_days_since_first_service'].mean()

#data def 44
def get_new_fam_dist_of_length_of_relationship(data: 'list[DataFrame]'):
    families = data[1]

    result_dict = {
        'bar 1':0,
        'bar 2':0,
        'bar 3':0,
        'bar 4':0,
        'bar 5':0,
        'bar 6':0,
        'bar 7':0,
        'bar 8':0,
        'bar 9':0,
        'bar 10':0,
    }

    set_max = 0;

    for index, row in families.iterrows():
        if int(row["max_days_since_first_service"]) > set_max:
            set_max = int(row["max_days_since_first_service"])

    width = set_max / 10

    for index, row in families.iterrows():

        max_days = int(row["max_days_since_first_service"])

        if max_days >= 0 and max_days < width:
            result_dict["bar 1"]+=1
        elif max_days >= width and max_days < (width*2):
            result_dict["bar 2"]+=1
        elif max_days >= (width*2) and max_days < (width*3):
            result_dict["bar 3"]+=1
        elif max_days >= (width*3) and max_days < (width*4):
            result_dict["bar 4"]+=1
        elif max_days >= (width*4) and max_days < (width*5):
            result_dict["bar 5"]+=1
        elif max_days >= (width*5) and max_days < (width*6):
            result_dict["bar 6"]+=1
        elif max_days >= (width*6) and max_days < (width*7):
            result_dict["bar 7"]+=1
        elif max_days >= (width*7) and max_days < (width*8):
            result_dict["bar 8"]+=1
        elif max_days >= (width*8) and max_days < (width*9):
            result_dict["bar 9"]+=1
        elif max_days >= (width*9) and max_days <= set_max:
            result_dict["bar 10"]+=1

    return json.dumps(result_dict)

#data def 45
def get_relationship_length_indv_mean(data):
    members = data[2]
    return members['max_days_since_first_service'].mean()

# data def 46
def get_new_fam_dist_of_length_of_relationships_for_individuals(data: 'list[DataFrame]'):
    members = data[2]

    result_dict = {
        'bar 1':0,
        'bar 2':0,
        'bar 3':0,
        'bar 4':0,
        'bar 5':0,
        'bar 6':0,
        'bar 7':0,
        'bar 8':0,
        'bar 9':0,
        'bar 10':0,
    }

    set_max = 0;

    for index, row in members.iterrows():
        if int(row["max_days_since_first_service"]) > set_max:
            set_max = int(row["max_days_since_first_service"])

    width = set_max / 10

    for index, row in members.iterrows():

        max_days = int(row["max_days_since_first_service"])

        if max_days >= 0 and max_days < width:
            result_dict["bar 1"]+=1
        elif max_days >= width and max_days < (width*2):
            result_dict["bar 2"]+=1
        elif max_days >= (width*2) and max_days < (width*3):
            result_dict["bar 3"]+=1
        elif max_days >= (width*3) and max_days < (width*4):
            result_dict["bar 4"]+=1
        elif max_days >= (width*4) and max_days < (width*5):
            result_dict["bar 5"]+=1
        elif max_days >= (width*5) and max_days < (width*6):
            result_dict["bar 6"]+=1
        elif max_days >= (width*6) and max_days < (width*7):
            result_dict["bar 7"]+=1
        elif max_days >= (width*7) and max_days < (width*8):
            result_dict["bar 8"]+=1
        elif max_days >= (width*8) and max_days < (width*9):
            result_dict["bar 9"]+=1
        elif max_days >= (width*9) and max_days <= set_max:
            result_dict["bar 10"]+=1

    return json.dumps(result_dict)


