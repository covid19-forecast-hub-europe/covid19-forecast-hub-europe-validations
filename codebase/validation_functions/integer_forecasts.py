# -*- coding: utf-8 -*-
"""
Created on Wed Jun  9 10:20:23 2021

@author: kaths
"""

import pandas as pd

def integer_values(file, warning_result):
    """
    Parameters
    ----------
    file : path

    Returns
    -------
    String containing a warning if file contains non-integer forecasts

    """
    
    df = pd.read_csv(file)
    non_integer = df["value"] != type(int)
    
    if non_integer.any():
        warning_result.append(f"Warning > non-integer value in forecast")
            
    return warning_result
