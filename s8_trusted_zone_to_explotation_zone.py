#  Exploitation zone creation
## Moving data tables from the trusted zone to the exploitation zone
### In the explotation zone data quality processes and data integration takes place
### This script automatically creates the exploitation zone database
import os
import duckdb
import pandas as pd
import numpy as np
from functools import reduce
from paths import temporalPath, trustedDataBasesDir, exploitationDatabasesDir


def getDataSourcesNames(temporalPath):
    """
            Getting a list with all the names of the data sources saved in the landing zone inside the temporal folder.
            Inside temporal folder there is one folder for landing each data source and their versions.

            @param:
                -    temporalPath: the absolute path of the temporal folder
            @Output:
                - data_sources_names: a list with all the names of the different datasources
    """
    for _, dirs, _ in os.walk(temporalPath):
        if len(dirs) > 0:
            data_sources_names = dirs
    return data_sources_names

def dataQualityProcesses ():
    # Add code here
    """# Creation of explotation zone database
    ## Data quality processes for integration - NCEI
    ### In this part NCEI data get aggregated to yearly level so they can be joined with WEB data 
    """

    # Getting the names of the different data sources
    data_sources_names = getDataSourcesNames(temporalPath)

    # Checking if exploitation databases directory exists, if not it is being created
    if not os.path.exists(exploitationDatabasesDir):
        os.mkdir(exploitationDatabasesDir)


    # Data quality processes for integration for each data source
    for data_source_name in data_sources_names:
        try:
            print(f"Data quality processes for integration - {data_source_name} data source \n")
            con = duckdb.connect(database=f'{trustedDataBasesDir}{data_source_name}_trusted.duckdb', read_only=False)
            df = con.execute(f'SELECT * FROM {data_source_name}').fetchdf()
            con.close()
            con1 = duckdb.connect(database=f'{exploitationDatabasesDir}{data_source_name}_exploitation_year_and_country.duckdb', read_only=False)

            if data_source_name == "NCEI":
                print(f"Aggregating - {data_source_name} data to YEARLY - COUNTRY LEVEL \n")
                df['YEAR'] = pd.DatetimeIndex(df['DATE']).year
                df['COUNTRY'] = df['NAME'].str[-2:]
                df = df.drop(["LATITUDE", "LONGITUDE", "ELEVATION", "MAX_ATTRIBUTES","MIN_ATTRIBUTES", "PRCP_ATTRIBUTES", "FRSHTT", "STATION", "SLP"], axis = 1)
                agg_df = df.groupby(['YEAR', 'COUNTRY'], as_index=False).agg("mean")
                years = agg_df['YEAR'].unique
                countries = agg_df['COUNTRY'].unique
                print(agg_df.head())
                table = data_source_name
                con1.execute(f'DROP TABLE IF EXISTS {table}')
                con1.execute(f'CREATE TABLE {table} AS SELECT * FROM agg_df')
            elif data_source_name == "WEB":
                print(f"Selecting specific years and countries from the trusted database of {data_source_name} data source \n")
                years = ["2018", "2019"]
                countries = ["Belgium"]
                interesting_cols = ["Country","Product", "Flow"]
                final_cols = interesting_cols + years
                df = df[final_cols]
                df = df.loc[df["Country"].isin(countries)]
                print(df.head())
                table = data_source_name
                con1.execute(f'DROP TABLE IF EXISTS {table}')
                con1.execute(f'CREATE TABLE {table} AS SELECT * FROM df')

            con1.close()
        except Exception as e:
            print(e)
            con.close()
            con1.close()

def dataIntegration ():
    # Getting the names of the different data sources
    data_sources_names = getDataSourcesNames(temporalPath)

    df_list =[]
    # Data integration from each data source to a single view table in exploitation database
    for data_source_name in data_sources_names:
        try:
            print(f"Data integration process \n")
            con = duckdb.connect(database=f'{exploitationDatabasesDir}{data_source_name}_exploitation_year_and_country.duckdb', read_only=False)
            df = con.execute(f'SELECT * FROM {data_source_name}').fetchdf()
            if data_source_name == "NCEI":
                col_names = df['YEAR'].T.values.tolist()
                col_names.insert(0, "Variables")
                df = df.T.reset_index()
                df.columns = col_names
                print(df.head())
            con.close()
            df_list.append(df)
        except Exception as e:
            print(e)
            con.close()
    if len(df_list) > 1:
        df = pd.concat(df_list, ignore_index=False, axis=1)
    else:
        df = df_list[0]
    con1 = duckdb.connect(database=f'{exploitationDatabasesDir}exploitation.duckdb', read_only=False)
    table = "VIEW"
    con1.execute(f'DROP TABLE IF EXISTS {table}')
    con1.execute(f'CREATE TABLE {table} AS SELECT * FROM df')
    con1.close()


def main():
    dataQualityProcesses()
    dataIntegration()

if __name__ == "__main__":
    main() #TODO NEEDS FIXING, TOO SLOW, NOT PLOTING EVENTUALLY