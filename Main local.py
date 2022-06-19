# -*- coding: utf-8 -*-
"""
Created on Wed Jun  8 21:14:22 2022

@author: hansv
"""
# -*- coding: utf-8 -*-
"""
Created on Thu May 26 21:40:48 2022

@author: hansv
"""
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import seaborn as sns
import squarify
import matplotlib
from matplotlib import pyplot as plt
from pandas_datareader import data
from requests_oauthlib import OAuth1Session
import json
import os
from google.cloud import storage
import io
import gcsfs

# constants
consumer_key = os.environ.get("CONSUMER_KEY")
consumer_secret = os.environ.get("CONSUMER_SECRET")
access_token = os.environ.get("ACCESS_TOKEN")
access_token_secret = os.environ.get("ACCESS_TOKEN_SECRET")

tickers = ['MAERSK-A.CO','MAERSK-B.CO','AMBU-B.CO','BAVA.CO','CARL-B.CO',
           'NOVO-B.CO','VWS.CO','ORSTED.CO','DANSKE.CO','FLS.CO',
           'ISS.CO','COLO-B.CO','HLUN-A.CO','HLUN-B.CO','DSV.CO','GN.CO',
           'CHR.CO','NZYM-B.CO','DEMANT.CO','GMAB.CO','JYSK.CO',
           'TRYG.CO','NETC.CO','PNDORA.CO','ROCK-B.CO','RBREW.CO']

names = pd.Series(['Mærsk A','Mærsk B','AMBU','Bavarian','Carlsberg',
        'Novo','Vestas','Ørsted','Danske Bank','FLS',
        'ISS','Coloplast','Lundbeck A','Lundbeck B','DSV','GN Store Nord',
        'Chr. Hansen','Novozymes','Demant','Genmab','Jyske Bank',
        'Tryg','Netcompany','Pandora','Rockwool','R. Unibrew'], name='Name')
names.index = tickers

today    = datetime.today()
today_7d = today - timedelta(days=7)

# Get the data from yahoo finance
def get_data():
    df = yf.download(tickers, start=today_7d.strftime('%Y-%m-%d'))
    return df

# Beregner det procentuelle afkast på den sidste dato i df
def get_pl_pct(df):
    close = df.loc[today_7d:today,'Adj Close']
    last_day = df.index[-1]
    secondlast_day =df.index[-2]
    pl_pct = pd.Series(close.loc[last_day] / close.loc[secondlast_day] - 1, name='PL')
    return pl_pct

# Henter seneste dags procentuelle undviklin i c25 
def get_c25index():
    df = yf.download('^OMXC25', start=today_7d.strftime('%Y-%m-%d'))
    pl_pct = get_pl_pct(df)
    return pl_pct[0]

# Create the treemap plot using squarify
def create_plot(df):
    pl_pct = get_pl_pct(df)
    marketcap = data.get_quote_yahoo(tickers)['marketCap']
    # justerer Maersk marketcap:
    marketcap['MAERSK-A.CO'] = marketcap['MAERSK-A.CO'] * 10334436 / (10334436 + 8372725)
    marketcap['MAERSK-B.CO'] = marketcap['MAERSK-B.CO'] * 8372725 / (10334436 + 8372725)
    samlet = pd.concat([names, marketcap, pl_pct], axis=1) 
    samlet = samlet.sort_values('marketCap', ascending=False)
    # laver plot
    sns.set_style(style="whitegrid") # set seaborn plot style
    sns.set(rc={'figure.figsize':(20,10)})
    sns.set
    matplotlib.rcParams['text.color'] = 'black'
    matplotlib.rcParams['font.size'] = 27
    cmap = (matplotlib.colors.ListedColormap(['red', 'salmon', '#32cd32','green'])
            .with_extremes(over='0.25', under='0.75'))
    bounds = [-0.5, -0.01, 0, 0.01, 0.5]
    norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)
    colors = [cmap(norm(value)) for value in samlet.PL.values]
    sizes = samlet.marketCap.values # proportions of the categories
    #Tager kun de 16 største ud af de 25 selskaber
    label = samlet.Name.values[0:16]
    value = ['{0:0.2%}'.format(s) for s in samlet.PL.values][0:16]
    # frasorterer labels og valus hvor marketcap er under threshold
    squarify.plot(sizes=sizes, label=label, value=value, ax=None, alpha=0.9,color=colors).set(title='')
    plt.axis('off')
    return plt
    # plt.savefig('treemapc25.png', bbox_inches='tight')
    
def create_table(df):
    pl_pct = get_pl_pct(df)
    fig = plt.figure(figsize=(16,12))
    ax = fig.add_subplot(111)
    # Set title
    ttl = 'Population, size and age expectancy in the European Union'
    # Set color transparency (0: transparent; 1: solid)
    a = 0.7
    # Create a colormap
    customcmap = [(x/24.0,  x/48.0, 0.05) for x in range(len(df))]
    # Plot the 'population' column as horizontal bar plot
df['population'].plot(kind='barh', ax=ax, alpha=a, legend=False, color=customcmap,
                      edgecolor='w', xlim=(0,max(df['population'])), title=ttl)
    
    

def save_figure(plt):
    fig_to_upload = plt.gcf()
    # Save figure image to a bytes buffer
    buf = io.BytesIO()
    fig_to_upload.savefig(buf, format='png', bbox_inches='tight', transparent=True, pad_inches=0)
    # init GCS client and upload buffer contents
    client = storage.Client()
    bucket = client.get_bucket('twitterbot-c25-bucket')
    blob = bucket.blob('treemapc25.png')  
    blob.upload_from_file(buf, content_type='image/png', rewind=True)


df = get_data()
plot = create_plot(df)
plot.savefig('c:/temp/treemapc255.png', bbox_inches=None)
c25udv = get_c25index()
c25udv_text = "{:.2%}".format(c25udv)
if c25udv > 0 :
    tweet_text = 'C25 steg med ' +  c25udv_text + ' i dag'
else:
    tweet_text = 'C25 faldt med ' + c25udv_text + ' i dag'

# fs = gcsfs.GCSFileSystem(project='twitterbot-c25')
# fs.ls('twitterbot-c25-bucket')
# files = {"media" : fs.open("gs://twitterbot-c25-bucket/treemapc25.png", 'rb')}


oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
)

#uploder fil til twitter 
response = oauth.post(
    "https://upload.twitter.com/1.1/media/upload.json",
    files = files,
)
media_id = json.loads(response.text)['media_id']

# poster fil på twitter
params = {'status': 'Aktier', "media_ids": [media_id]}
response = oauth.post("https://api.twitter.com/1.1/statuses/update.json", params = params) 
   



