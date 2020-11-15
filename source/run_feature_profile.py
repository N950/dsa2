# -*- coding: utf-8 -*- 
"""


python run_feature_profile.py run_profile  --path_data data/input/titanic/train/ --path_output data/out/titanic/profile



"""
import gc
import os
import logging
from datetime import datetime
import warnings
import numpy as np
import pandas as pd

import pandas_profiling as pp

###################################################################
#### Add path for python import
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/")
import util_feature


#### Root folder analysis
root = os.path.abspath(os.getcwd()).replace("\\", "/") + "/"
print(root)




############CLI Command ############################################################################
def run_profile(path_data=None,  path_output="data/out/ztmp/", n_sample=5000):
    """
      Use folder , filename are fixed.

    """
    path_output = root + path_output
    path_data   = root + path_data
    os.makedirs(path_output, exist_ok=True)
    log(path_output)

    path_train_X   = path_data   + "/features.csv"
    path_train_y   = path_data   + "/target.csv"

    log("#### load input column family  ###################################################")
    cols_group = json.load(open(path_data + "/cols_group.json", mode='r'))
    log(cols_group)


    ##### column names for feature generation ###############################################
    log(cols_group)
    coly            = cols_group['coly']  # 'salary'
    colid           = cols_group['colid']  # "jobId"
    colcat          = cols_group['colcat']  # [ 'companyId', 'jobType', 'degree', 'major', 'industry' ]
    colnum          = cols_group['colnum']  # ['yearsExperience', 'milesFromMetropolis']
    
    colcross_single = cols_group.get('colcross', [])   ### List of single columns
    #coltext        = cols_group.get('coltext', [])
    coltext         = cols_group['coltext']
    coldate         = cols_group.get('coldate', [])
    colall          = colnum + colcat + coltext + coldate
    log(colall)


	#coly = 'Survived'
	#colid = "PassengerId"
	#colcat = [ 'Sex', 'Embarked']
	#colnum = ['Pclass', 'Age','SibSp', 'Parch','Fare']
	#coltext = ['Name','Ticket']
	#coldate = []

	#### Pandas Profiling for features in train  ######################
	df = pd.read_csv( path_train_X ) # path + f"/new_data/Titanic_Features.csv")

	try :
   	    dfy = pd.read_csv(path_train_y # + f"/new_data/Titanic_Labels.csv")
	    df  = pd.nerge(df, dfy, on =colid,  how="left")
    except : 
    	pass

	df = df.set_index(colid)
	for x in colcat:
	    df[x] = df[x].factorize()[0]

	profile = df.profile_report(title='Profile data')
	profile.to_file(output_file=path_output + "/00_features_report.html")


    log("######### finish #################################", )


if __name__ == "__main__":
    import fire
    fire.Fire()




"""


	#### Test dataset  ################################################
	df = pd.read_csv(path + f"/new_data/Titanic_test.csv")
	df = df.set_index(colid)
	for x in colcat:
	    df[x] = df[x].factorize()[0]

	profile = df.profile_report(title='Profile Test data')
	profile.to_file(output_file=path + "/analysis/00_features_test_report.html")



    log("#### Preprocess  #################################################################")
    preprocess_pars = model_dict['model_pars']['pre_process_pars']
    filter_pars     = model_dict['data_pars']['filter_pars']    
    dfXy, cols = preprocess(path_train_X, path_train_y, path_pipeline_out, cols_group, n_sample, 
                            preprocess_pars, filter_pars)
    model_dict['data_pars']['coly'] = cols['coly']
    


    log("######### export #################################", )
    os.makedirs(path_check_out, exist_ok=True)
    colexport = [cols['colid'], cols['coly'], cols['coly'] + "_pred"]
    dfXy[colexport].to_csv(path_check_out + "/pred_check.csv")  # Only results
    #dfXy.to_parquet(path_check_out + "/dfX.parquet")  # train input data
    dfXy.to_csv(path_check_out + "/dfX.csv")  # train input data

    #dfXytest.to_parquet(path_check_out + "/dfXtest.parquet")  # Test input data
    dfXytest.to_csv(path_check_out + "/dfXtest.csv")  # Test input data

    lo