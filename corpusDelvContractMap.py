import pandas as pd
from datetime import datetime as dt
import matplotlib.pyplot as plt
from IPython.display import display
import pyodbc
import config as cf
import requests
import os

from flask import Flask, render_template
app = Flask(__name__)

conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+cf.server+';DATABASE='+cf.database+';UID='+cf.username+';PWD='+ cf.pwd)
cursor = conn.cursor()

@app.route('/')
def displayMap():
    if not os.path.isfile('contracts.csv'):
        api_key = cf.api_key
        address_df = pd.read_sql_query('''
            SELECT *
            FROM OPENQUERY (
                [PRODUCTION],
                    'SELECT C.FULL_NAME AS customerName
                        , A.ADDRESS_LINE_1 AS addLine1
                        , A.CITY AS city
                        , A.STATE AS state
                        , A.ZIP AS zip
                        , C.VSM_FUTURE_DELIVERIES AS futureDeliveryDates
                        , DC.DW_CONTRACT_NUMBER AS contractNumber
                        , CT.LIST_ITEM_NAME AS contractType
                        , DF.LIST_ITEM_NAME AS deliveryFrequency
                        , I.NAME AS item
                        , DI.SUGGESTED_QTY AS suggestedQty
                        , A.GOOGLE_VALIDATED_LATITUDE AS latitude
                        , A.GOOGLE_VALIDATED_LONGITUDE AS longitude
                    FROM [Driessen Water, Inc_].[DW Data Admin].[CUSTOMERS] C
                        JOIN [Driessen Water, Inc_].[DW Data Admin].[DW_CONTRACT] DC
                            ON DC.CUSTOMER_ID = C.CUSTOMER_ID
                                AND C.SUBSIDIARY_ID = 16
                        JOIN [Driessen Water, Inc_].[DW Data Admin].[DELIVERY_ITEMS] DI
                            ON DI.DELIVERY_LINK_ID = DC.DW_CONTRACT_ID
                                AND DC.CONTRACT_STATUS_ID = 1
                                AND DC.IS_INACTIVE = ''F''
                        JOIN [Driessen Water, Inc_].[DW Data Admin].[ITEMS] I
                            ON I.ITEM_ID = DI.DELIVERY_ITEM_ID
                        JOIN [Driessen Water, Inc_].[DW Data Admin].[DELIVERY_FREQUENCY] DF
                            ON DF.LIST_ID = DI.DELIVERY_FREQUENCY_ID
                                AND DF.LIST_ITEM_NAME != ''Will Call''
                        JOIN [Driessen Water, Inc_].[DW Data Admin].[CONTRACT_TYPE] CT
                            ON CT.LIST_ID = DC.CONTRACT_TYPE_ID
                        JOIN [Driessen Water, Inc_].[DW Data Admin].[ADDRESS_BOOK] AB
                            ON AB.ENTITY_ID = C.CUSTOMER_ID
                                AND AB.IS_DEFAULT_SHIP_ADDRESS = ''Yes'' 
                                AND AB.IS_INACTIVE = ''No'' 
                        JOIN [Driessen Water, Inc_].[DW Data Admin].[ADDRESSES] A
                            ON A.ADDRESS_ID = AB.ADDRESS_ID')''',conn)
        
        address = ''
        cityState = ''

        for i, row in address_df.iterrows():
            address = row["addLine1"].replace(' ','+')
            cityState = row["city"] + ',+' + row['state'].strip()
            requestStr = f'https://maps.googleapis.com/maps/api/geocode/json?address={address},{cityState}&key={api_key}'
            # endpoint = f"{base_url}?address={address_or_zipcode}&key={api_key}"
            # see how our endpoint includes our API key? Yes this is yet another reason to restrict the key
            
            try:
                if row['latitude'] == None:
                    requestJSON = requests.get(requestStr)
                    results = requestJSON.json()['results'][0]
                    print(results)
                    if results['geometry']['location_type'] == 'ROOFTOP':
                        lat = results['geometry']['location']['lat']
                        lng = results['geometry']['location']['lng']
                        g_addLine1 = results['address_components'][0]['long_name'] + ' ' + results['address_components'][1]['long_name']
                        g_city = results['address_components'][2]['long_name']
                        g_county = results['address_components'][3]['long_name']
                        g_zip = results['address_components'][5]['long_name']
                        #print(g_addLine1)     

                        address_df.loc[i, 'longitude'] = lng
                        address_df.loc[i, 'latitude'] = lat
                        address_df.loc[i, 'g_addLine1'] = g_addLine1
                        address_df.loc[i, 'g_city'] = g_city
                        address_df.loc[i, 'g_county'] = g_county
                        address_df.loc[i, 'g_zip'] = g_zip
                        address_df.loc[i, 'g_valid'] = 'Y'
                    else:
                        address_df.loc[i, 'g_valid'] = 'N'
            except:
                print('Error on a line')

        address_df.to_csv('contracts.csv', index=False)
    else:
        print('File already exists')

    return render_template('index.html')

if __name__ == "__main__":
    app.run()
