#!/usr/bin/env python3

import billiard as mp
import twitterdata
import csv_utils
import pprint
from sightengine.client import SightengineClient
from creds import client_access, all_creds, current_cred
import requests
import json
import sys
import os

from app import celery_app

client = SightengineClient(all_creds[current_cred][0], all_creds[current_cred][1])

def getOutput(my_url_list):
    global client, all_creds, current_cred
    output_list = []
    for my_url in my_url_list:
        if current_cred >= len(all_creds):
            current_cred = 0
            raise Exception('You have reached the daily limit of 1500 requests!')
            break
        result = client.check('wad').set_url(my_url)
        while result['status'] != 'success':
            result = client.check('wad').set_url(my_url)
            print(result)
            if result['status'] == 'success':
                print('Trying credentials ' + all_creds[current_cred][0] + ', ' + all_creds[current_cred][1])
                break
            else:
                current_cred += 1
            if current_cred >= (len(all_creds)): # if last credential reached
                current_cred = 0
                raise Exception('API keys exhausted.')
                break
            print('Trying credentials ' + all_creds[current_cred][0] + ', ' + all_creds[current_cred][1])
            client = SightengineClient(all_creds[current_cred][0], all_creds[current_cred][1])
        print('SUCCESS: using credentials ' + all_creds[current_cred][0] + ', ' + all_creds[current_cred][1])
        print(result)
        output_list.append(result)
    for output in output_list:  print(output)
    return output_list

def checkDrugs(output_list):
    my_drug_list = []
    for output in output_list:
        print(output)
        drugs = output['drugs']
        my_drug_list.append(drugs)
    return my_drug_list

def checkWeapons(output_list):
    my_weapon_list = []
    for output in output_list:
        weapons = output['weapon']
        my_weapon_list.append(weapons)
    return my_weapon_list

def checkAlcohol(output_list):
    my_alcohol_list = []
    for output in output_list:
        alcohol = output['alcohol']
        my_alcohol_list.append(alcohol)
    return my_alcohol_list

def gen_list(count):
    my_list = []
    for i in range(count):
        my_list.append(i)
    return my_list

pp = pprint.PrettyPrinter(indent=4)

# helper function - DO NOT use this outside this file
def wad_helper(output_list, query_type):
    results = []
    for output in output_list:
        print(output)
        res = output[query_type]
        results.append(res)
    return results
    sys.exit(0)

@celery_app.task(bind=True)
def concurrent_twitter_query_wad(self, username, tweets_num=10, threads=2):
    if current_cred >= len(all_creds):
        raise Exception('API keys exhausted.')
    try:
        all_tweets = twitterdata.get_all_tweets(username, tweets_num)
    except:
        raise
    try:
        tweets_output = getOutput(all_tweets)
    except:
        raise
    pool = mp.Pool(threads)
    try:
        pool_results = pool.starmap(wad_helper, [(tweets_output, 'weapon'), (tweets_output, 'drugs'), (tweets_output, 'alcohol')])
        self.update_state(state="PROGRESS")
    except:
        raise
    finally:
        pool.terminate()
    weapon_vals = pool_results[0]
    drug_vals = pool_results[1]
    alcohol_vals = pool_results[2]
    print('Data acquired concurrently for user: ' + username)
    result = {
        'weapons' : weapon_vals,
        'alcohol' : alcohol_vals,
        'drugs'   : drug_vals
    }
    result = {username : result}
    print(result)
    self.update_state("FINISHED")
    return {"result" : result}

def twitter_query_wad(username, tweets_num):
    try:
        all_tweets = twitterdata.get_all_tweets(username, tweets_num)
    except:
        raise
    try:
        tweets_output = getOutput(all_tweets)
    except:
        raise
    weapon_vals = checkWeapons(tweets_output)
    alcohol_vals = checkAlcohol(tweets_output)
    drug_vals = checkDrugs(tweets_output)
    print('Data acquired for user: ' + username)
    result = {
        'weapons' : weapon_vals,
        'alcohol' : alcohol_vals,
        'drugs'   : drug_vals
    }
    print(result)
    return result

# twitter_bulk_query_wad() - process and return the Weapons/Alcohol/Drugs content of multiple Twitter usernames
# example usage: twitter_bulk_query_wad(['POTUS', 'narendramodi'], threads=4)
@celery_app.task(bind=True)
def twitter_bulk_query_wad(self, user_list, tweets_num=10, threads=2):
    if current_cred >= len(all_creds):
        raise Exception('You have reached the daily limit of 1500 requests!')
    print(user_list)
    results = {}
    pool = mp.Pool(threads)
    try:
        pool_results = pool.starmap(twitter_query_wad, [(user, tweets_num) for user in user_list])
        self.update_state(state="PROGRESS")
    except:
        raise
    finally:
        pool.terminate()
    results = [{user_list[i] : pool_results[i]} for i in range(len(user_list))]
    print('twitter_bulk_query_wad() completed.')
    self.update_state(state="FINISHED")
    print(results)
    return {"result" : results}

def check_user_exists(user):
    my_response = requests.get("https://twitter.com/users/username_available?username="+str(user))
    my_response = my_response._content
    my_response = my_response.decode("utf-8")
    my_response = my_response.replace("''","\"")
    print("\n\n" + str(my_response) + "\n\n")
    my_response = json.loads(my_response)
    print(my_response)
    my_response = my_response['valid']
    return not my_response
