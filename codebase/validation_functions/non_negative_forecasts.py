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
    negative = df["value"]<0
    
    
    if negative.any():
        result.append(f"Warning > negative value in forecast")
            
    return result