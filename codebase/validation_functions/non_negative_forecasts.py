# -*- coding: utf-8 -*-
"""
Created on Fri Mar 26 15:18:25 2021

@author: Jannik
"""

import pandas as pd

def non_negative_values(file):
    """
    Parameters
    ----------
    file : path

    Returns
    -------
    String containing a warning if file contains negative forecasts

    """
    
    result = []
    
    df = pd.read_csv(file)
    negative = df["value"]>0
    
    
    if negative.any():
        result.append(f": negative value in forecast")
            
    non_integer = df["value"] != round(df["value"])
    
    if non_integer.any():
        result.append(f" : non-integer value in forecast")

    if len(result) > 0:
        result = 'Warnings' + ''.join(result)
    
    return result
