# pylint: disable=C0321,C0103,E1221,C0301,E1305,E1121,C0302,C0330
# -*- coding: utf-8 -*-
"""

python source/run_train.py  run_train --config_name elasticnet  --path_data_train data/input/train/    --path_output data/output/a01_elasticnet/

activate py36 && python source/run_train.py  run_train   --n_sample 100  --config_name lightgbm  --path_model_config source/config_model.py  --path_output /data/output/a01_test/     --path_data_train /data/input/train/

"""
import warnings,sys, os, json, importlib, copy
warnings.filterwarnings('ignore')

####################################################################################################
#### Add path for python import
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/")
root = os.path.abspath(os.getcwd()).replace("\\", "/") + "/"
print(root)

####################################################################################################
try   : verbosity = int(json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/../config.json", mode='r'))['verbosity'])
except Exception as e : verbosity = 4
#raise Exception(f"{e}")

def log(*s):
    print(*s, flush=True)

def log2(*s):
    if verbosity >= 2 : print(*s, flush=True)

def log3(*s):
    if verbosity >= 3 : print(*s, flush=True)


####################################################################################################
from util_feature import   load, save_list, load_function_uri, save
from run_preprocess import  preprocess, preprocess_load

def save_features(df, name, path):
    if path is not None :
       os.makedirs( f"{path}/{name}", exist_ok=True)
       df.to_parquet( f"{path}/{name}/features.parquet")


def model_dict_load(model_dict, config_path, config_name, verbose=True):
    """ Load the model dict from the python config file.
       ### Issue wiht passing function durin pickle on disk
    :return:
    """
    if model_dict is None :
      log("#### Model Params Dynamic loading  ###############################################")
      model_dict_fun = load_function_uri(uri_name=config_path + "::" + config_name)
      model_dict    = model_dict_fun()   ### params 

    else :
        ### Passing dict 
        ### Due to Error when saving on disk the model, function definition is LOST, need dynamic load
        path_config = model_dict[ 'global_pars']['config_path']

        p1 = path_config + "::" + model_dict['model_pars']['post_process_fun'].__name__
        model_dict['model_pars']['post_process_fun'] = load_function_uri( p1)   

        p1 = path_config + "::" + model_dict['model_pars']['pre_process_pars']['y_norm_fun'] .__name__ 
        model_dict['model_pars']['pre_process_pars']['y_norm_fun'] = load_function_uri( p1 ) 

    return model_dict


####################################################################################################
##### train    #####################################################################################
def map_model(model_name):
    """
      Get the Class of the object stored in source/models/
    :param model_name:   model_sklearn
    :return: model module

    """
    ##### Custom folder
    if ".py" in model_name :
       model_file = model_name.split(":")[0]    
       ### Asbolute path of the file
       path = os.path.dirname(os.path.abspath(model_file))
       sys.path.append(path)
       mod    = os.path.basename(model_file).replace(".py", "")
       modelx = importlib.import_module(mod)
       return modelx

    ##### Repo folder
    model_file = model_name.split(":")[0]
    if  'optuna' in model_name : model_file = 'optuna_lightgbm'

    try :
       ##  'models.model_bayesian_pyro'   'model_widedeep'
       mod    = f'models.{model_file}'
       modelx = importlib.import_module(mod)

    except :
        ### All SKLEARN API
        ### ['ElasticNet', 'ElasticNetCV', 'LGBMRegressor', 'LGBMModel', 'TweedieRegressor', 'Ridge']:
       mod    = 'models.model_sklearn'
       modelx = importlib.import_module(mod)

    return modelx

def train(model_dict, dfX, cols_family, post_process_fun):
    """  Train the model using model_dict, save model, save prediction
    :param model_dict:  dict containing params
    :param dfX:  pd.DataFrame
    :param cols_family: dict of list containing column names
    :param post_process_fun:
    :return: dfXtrain , dfXval  DataFrame containing prediction.
    """
    model_pars, compute_pars = model_dict['model_pars'], model_dict['compute_pars']
    data_pars                = model_dict['data_pars']
    model_name, model_path   = model_pars['model_class'], model_dict['global_pars']['path_train_model']
    metric_list              = compute_pars['metric_list']

    assert  'cols_model_type2' in data_pars, 'Missing cols_model_type2, split of columns by data type '
    log2(data_pars['cols_model_type2'])


    log("#### Model Input preparation ##################################################")
    log2(dfX.shape)
    dfX    = dfX.sample(frac=1.0)
    itrain = int(0.6 * len(dfX))
    ival   = int(0.8 * len(dfX))
    colsX  = data_pars['cols_model']
    coly   = data_pars['coly']
    log2('Model colsX',colsX)
    log2('Model coly', coly)
    log2('Model column type: ',data_pars['cols_model_type2'])

    ### Only Parameters
    data_pars_ref = copy.deepcopy(data_pars)

    #### TODO : Lazy Dict to have large dataset
    data_pars['data_type'] = 'ram'
    data_pars['train'] = {'Xtrain' : dfX[colsX].iloc[:itrain, :],
                          'ytrain' : dfX[coly].iloc[:itrain],
                          'Xtest'  : dfX[colsX].iloc[itrain:ival, :],
                          'ytest'  : dfX[coly].iloc[itrain:ival],

                          'Xval'   : dfX[colsX].iloc[ival:, :],
                          'yval'   : dfX[coly].iloc[ival:],
                          }

    log("#### Init, Train ############################################################")
    # from config_model import map_model    
    modelx = map_model(model_name)    
    log2(modelx)
    modelx.reset()
    ###  data_pars_ref has NO data.
    modelx.init(model_pars, data_pars= data_pars_ref, compute_pars=compute_pars)

    ### Using Actual daa in data_pars['train']
    modelx.fit(data_pars, compute_pars)


    log("#### Predict ################################################################")
    ypred, ypred_proba = modelx.predict(dfX[colsX], data_pars= data_pars_ref, compute_pars=compute_pars)

    dfX[coly + '_pred'] = ypred  # y_norm(ypred, inverse=True)

    dfX[coly]            = dfX[coly].apply(lambda  x : post_process_fun(x) )
    dfX[coly + '_pred']  = dfX[coly + '_pred'].apply(lambda  x : post_process_fun(x) )

    if ypred_proba is None :  ### No proba
        ypred_proba_val = None

    elif len(ypred_proba.shape) <= 1  :  #### Single dim proba
       ypred_proba_val      = ypred_proba[ival:]
       dfX[coly + '_proba'] = ypred_proba

    elif len(ypred_proba.shape) > 1 :   ## Muitple proba
        from util_feature import np_conv_to_one_col
        ypred_proba_val      = ypred_proba[ival:,:]
        dfX[coly + '_proba'] = np_conv_to_one_col(ypred_proba, ";")  ### merge into string "p1,p2,p3,p4"
        log(dfX.head(3).T)

    log2("Actual    : ",  dfX[coly ])
    log2("Prediction: ",  dfX[coly + '_pred'])

    log("#### Metrics ###############################################################")
    from util_feature import  metrics_eval
    metrics_test = metrics_eval(metric_list,
                                ytrue       = dfX[coly].iloc[ival:],
                                ypred       = dfX[coly + '_pred'].iloc[ival:],
                                ypred_proba = ypred_proba_val )
    stats = {'metrics_test' : metrics_test}
    log(stats)


    log("### Saving model, dfX, columns #############################################")
    log2(model_path + "/model.pkl")
    os.makedirs(model_path, exist_ok=True)
    save(colsX, model_path + "/colsX.pkl")
    save(coly,  model_path + "/coly.pkl")
    modelx.save(model_path, stats)


    log("### Reload model,            ###############################################")
    log2(modelx.model.model_pars, modelx.model.compute_pars)
    modelx = map_model(model_name)
    modelx.load_model(model_path )
    log("Reload model pars", modelx.model.model_pars)
    log2("Reload model", modelx.model)

    return dfX.iloc[:ival, :].reset_index(), dfX.iloc[ival:, :].reset_index(), stats


####################################################################################################
############CLI Command ############################################################################
def cols_validate(model_dict):
    """  Validate dictionnary
    :param model_dict:
    :return:
    """
    cols_input_type   = model_dict['data_pars']['cols_input_type']
    cols_prepro_in    = [   t['cols_family']  for t in model_dict['model_pars']['pre_process_pars']['pipe_list']  ]
    cols_prepro_out   = [   t['cols_out']     for t in model_dict['model_pars']['pre_process_pars']['pipe_list']  ]
    cols_model_in     = model_dict['data_pars']['cols_model_group']
    cols_model_type   = [ col_list  for k,col_list in  model_dict['data_pars']['cols_model_type'].items() ]
    cols_model_type   = sum(cols_model_type, [])

    for t in cols_prepro_in :
       if  not t  in cols_input_type and not t  in cols_prepro_out  : raise Exception(f"Missing prepro col {t} in cols_input_type")

    for t in cols_model_in :
       if  not t  in cols_prepro_out and not t in cols_input_type: raise Exception(f"Missing cols_model_group {t} in cols_input_type, prepro cols_out")

    for t in cols_model_type :
       if  not t  in cols_prepro_out and not t in cols_input_type: raise Exception(f"Missing cols_model_type {t} in cols_input_type, prepro cols_out")

    log('#######  colgroup names are valid')


def run_train(config_name, config_path="source/config_model.py", n_sample=5000,
              mode="run_preprocess", model_dict=None, return_mode='file', **kw):
    """
      Configuration of the model is in config_model.py file
    :param config_name:
    :param config_path:
    :param n_sample:
    :return:
    """
    model_dict  = model_dict_load(model_dict, config_path, config_name, verbose=True)

    m           = model_dict['global_pars']
    path_data_train   = m['path_data_train']
    path_train_X      = m.get('path_train_X', path_data_train + "/features.zip") #.zip
    path_train_y      = m.get('path_train_y', path_data_train + "/target.zip")   #.zip

    path_output         = m['path_train_output']
    # path_model          = m.get('path_model',          path_output + "/model/" )
    path_pipeline       = m.get('path_pipeline',       path_output + "/pipeline/" )
    path_features_store = m.get('path_features_store', path_output + '/features_store/' )  #path_data_train replaced with path_output, because preprocessed files are stored there
    path_check_out      = m.get('path_check_out',      path_output + "/check/" )
    log(path_output)


    log("#### load raw data column family, colum check  ###################################")
    cols_validate(model_dict)
    cols_group = model_dict['data_pars']['cols_input_type']  ### Raw
    log2(cols_group)


    log("#### Preprocess  ################################################################")
    preprocess_pars = model_dict['model_pars']['pre_process_pars']
     
    if mode == "run_preprocess" :
        dfXy, cols      = preprocess(path_train_X, path_train_y,
                                     path_pipeline,    ### path to save preprocessing pipeline
                                     cols_group,       ### dict of column family
                                     n_sample,
                                     preprocess_pars,
                                     path_features_store  ### Store intermediate dataframe
                                     )

    elif mode == "load_preprocess"  :  #### Load existing data
        dfXy, cols      = preprocess_load(path_train_X, path_train_y, path_pipeline, cols_group, n_sample,
                                          preprocess_pars,  path_features_store=path_features_store)


    log("#### Extract column names  #####################################################")
    ### Actual column names for Model Input :  label y and Input X (colnum , colcat), remove duplicate names
    model_dict['data_pars']['coly']       = cols['coly']
    model_dict['data_pars']['cols_model'] = list(set(sum([  cols[colgroup] for colgroup in model_dict['data_pars']['cols_model_group'] ]   , []) ))


    #### Flatten Col Group by column type : Sparse, continuous, .... (ie Neural Network feed Input, remove duplicate names
    ## 'coldense' = [ 'colnum' ]     'colsparse' = ['colcat' ]
    model_dict['data_pars']['cols_model_type2'] = {}
    for colg, colg_list in model_dict['data_pars'].get('cols_model_type', {}).items() :
        model_dict['data_pars']['cols_model_type2'][colg] = list(set(sum([  cols[colgroup] for colgroup in colg_list ]   , [])))


    log("#### Train model: #############################################################")
    log3(str(model_dict)[:1000])
    post_process_fun      = model_dict['model_pars']['post_process_fun']
    dfXy, dfXytest,stats  = train(model_dict, dfXy, cols, post_process_fun)


    log("#### Register model ##########################################################")
    mlflow_pars = model_dict.get('compute_pars', {}).get('mlflow_pars', None)
    if mlflow_pars is not None:
        mlflow_register(dfXy, model_dict, stats, mlflow_pars)


    log("#### Export ##################################################################")
    if return_mode == 'dict' :
        return { 'dfXy' : dfXy, 'dfXytest': dfXytest, 'stats' : stats   }

    else :        
        os.makedirs(path_check_out, exist_ok=True)
        colexport = [cols['colid'], cols['coly'], cols['coly'] + "_pred"]
        if cols['coly'] + '_proba' in  dfXy.columns :
            colexport.append( cols['coly'] + '_proba' )
        dfXy[colexport].to_csv(path_check_out + "/pred_check.csv", sep="\t")  # Only results

        dfXy.to_parquet(path_check_out + "/dfX.parquet")  # train input data generate parquet
        dfXytest.to_parquet(path_check_out + "/dfXtest.parquet")  # Test input data  generate parquet

        #dfXy.to_csv(path_check_out + "/dfX.csv")  # train input data generate csv
        #dfXytest.to_csv(path_check_out + "/dfXtest.csv")  # Test input data  generate csv
        log("######### Finish #############################################################", )



def run_model_check(path_output, scoring):
    """
    :param path_output:
    :param scoring:
    :return:
    """
    import pandas as pd
    try :
        #### Load model
        from source.util_feature import load
        from source.models import model_sklearn as modelx
        import sys
        from source import models
        sys.modules['models'] = models

        dir_model    = path_output
        modelx.model = load( dir_model + "/model/model.pkl" )
        stats        = load( dir_model + "/model/info.pkl" )
        colsX        = load( dir_model + "/model/colsX.pkl"   )
        coly         = load( dir_model + "/model/coly.pkl"   )
        print(stats)
        print(modelx.model.model)

        ### Metrics on test data
        log(stats['metrics_test'])

        #### Loading training data  ######################################################
        dfX     = pd.read_csv(dir_model + "/check/dfX.csv")  #to load csv
        #dfX = pd.read_parquet(dir_model + "/check/dfX.parquet")    #to load parquet
        dfy     = dfX[coly]
        colused = colsX

        dfXtest = pd.read_csv(dir_model + "/check/dfXtest.csv")    #to load csv
        #dfXtest = pd.read_parquet(dir_model + "/check/dfXtest.parquet"    #to load parquet
        dfytest = dfXtest[coly]
        print(dfX.shape,  dfXtest.shape )


        #### Feature importance on training data  #######################################
        from util_feature import  feature_importance_perm
        lgb_featimpt_train,_ = feature_importance_perm(modelx, dfX[colused], dfy,
                                                       colused,
                                                       n_repeats=1,
                                                       scoring=scoring)
        print(lgb_featimpt_train)
    except :
        pass






def mlflow_register(dfXy, model_dict: dict, stats: dict, mlflow_pars:dict ):
    log("#### Using mlflow #########################################################")
    # def register(run_name, params, metrics, signature, model_class, tracking_uri= "sqlite:///local.db"):
    from run_mlflow import register
    from mlflow.models.signature import infer_signature

    train_signature = dfXy[model_dict['data_pars']['cols_model']]
    y_signature     = dfXy[model_dict['data_pars']['coly']]
    signature       = infer_signature(train_signature, y_signature)

    register( run_name    = model_dict['global_pars']['config_name'],
             params       = model_dict['global_pars'],
             metrics      = stats["metrics_test"],
             signature    = signature,
             model_class  = model_dict['model_pars']["model_class"],
             tracking_uri = mlflow_pars.get( 'tracking_db', "sqlite:///mlflow_local.db")
            )




if __name__ == "__main__":
    import fire
    fire.Fire()




