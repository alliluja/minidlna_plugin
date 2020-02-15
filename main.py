#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import json #json

from common_classes import CDBworker

def getConfig():
    with open("config.json", "r") as configFile:
        config = json.load(configFile)
    return config

Config = getConfig()

worker = CDBworker(Config)