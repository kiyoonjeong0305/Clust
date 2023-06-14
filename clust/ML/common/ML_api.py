import sys

sys.path.append("../")
sys.path.append("../../")
sys.path.append("../../../")

from sklearn.metrics import classification_report
from Clust.clust.tool.stats_table import metrics
from Clust.clust.ML.tool import scaler as ml_scaler
from Clust.clust.ML.tool import data as ml_data
from Clust.clust.ML.common import ML_pipeline

def chagne_type_str_to_bool(dict_data):

    for key, value in dict_data.items():

        if isinstance(value, dict):
            dict_data[key] = chagne_type_str_to_bool(value)

        elif isinstance(value, str):

            if value.lower() == 'true':
                dict_data[key] = True
            elif value.lower() == 'false':
                dict_data[key] = False
            elif value.lower() == 'none':
                dict_data[key] = None

    return dict_data

def check_model_name(model_name, model_name_info):
    """It makes model name by default value and additional information

    Args:
        model_name (string): default model name
        model_name_info (array): model name information

    Returns:
        model_name(str): final model name
    """
    # model name & path
    if model_name is None or model_name == 'None':
        model_name=""
        for key in model_name_info:
            model_name+=key+'_'
        
    return model_name

def get_train_data_meta(meta_client, params):
    """get train data meta information

    Args:
        meta_client (mongodb client):mongodb
        params (dict): it must include 'bk_name_X', and 'ms_name_X' keys.

    Returns:
        result(dict): measurement information meta
    """
    bk_name = params['bucket_name']
    ms_name = params['ms_name']
    data_meta = meta_client.get_document_by_json(bk_name, ms_name, {'ms_name': ms_name})  
    try:
        result = data_meta[0]
    except:
        result = {}
        
    return result

def ML_data_preparation(param, influxdb_client):
    # 1. Oirignla data ingestion
    data_X, data_y = ML_pipeline.Xy_data_preparation(param['ingestion_param_X'], 
                                                 param['data_y_flag'], 
                                                 param['ingestion_param_y'],
                                                 'ms_all', 
                                                 influxdb_client)
    # 2. Scaling
    dataX_scaled, datay_scaled = ML_pipeline.Xy_data_scaling_train(param['ingestion_param_X']['ms_name'], 
                                                                                     data_X, 
                                                                                     param['ingestion_param_y']['ms_name'], 
                                                                                     data_y, 
                                                                                     param['scaler_param'])
    
    
    
    # 3.clean column
    dataX_scaled = ML_pipeline.clean_low_quality_column(dataX_scaled, 
                                                        param['transform_param'])

    # 4. split train/Val
    split_ratio = 0.8
    train_X, val_X, train_y, val_y, param['transform_param']= ML_pipeline.split_data_by_mode(dataX_scaled, 
                                                                                             datay_scaled, 
                                                                                             split_ratio, 
                                                                                             param['transform_param'])
    
    # 5. Transform array style
    train_X_array, train_y_array = ML_pipeline.transform_data_by_split_mode(param['transform_param'], 
                                                                            train_X, 
                                                                            train_y)
    val_X_array, val_y_array = ML_pipeline.transform_data_by_split_mode(param['transform_param'], 
                                                                        val_X, 
                                                                        val_y)
        
        
    
    return train_X_array, train_y_array, val_X_array, val_y_array

def ML_training(train_X_array,  train_y_array, val_X_array, val_y_array, param):
    # model info update

    from Clust.clust.ML.common import model_parameter_setting
    param['model_info']['seq_len'] = train_X_array.shape[1] 
    param['model_info']['input_size'] = train_X_array.shape[2] 
    param['model_info']['model_parameter'] = model_parameter_setting.set_model_parameter(param['model_info']) 
    model_info = param['model_info']

    from Clust.clust.ML.tool import model as ml_model
    train_data_path_list = [model_info['model_name'] , param['ingestion_param_X']['ms_name']]
    model_file_path = ml_model.get_model_file_path(train_data_path_list, model_info['model_method'] )


    param['model_info']['model_file_path'] = {
        "modelFile":{
            "fileName":"model.pth",
            "filePath":model_file_path
        }
    }

    # model training
    # input 순서 일관되도록 펑션 수정
    if model_info['model_purpose'] == 'regression':    
        ML_pipeline.CLUST_regresstion_train(train_X_array, 
                                            train_y_array, 
                                            val_X_array, 
                                            val_y_array,
                                            param['model_info']
                                            )
    elif model_info['model_purpose']  == 'classification':
        ML_pipeline.CLUST_classification_train(train_X_array, 
                                               train_y_array, 
                                               val_X_array, 
                                               val_y_array, 
                                               param['model_info'])


    return param


def test_data_preparation(params, model_meta, db_client):

    data_X, data_y = ML_pipeline.Xy_data_preparation(params['ingestion_param_X'], params['data_y_flag'], params['ingestion_param_y'], 'ms_all', db_client)

    test_X, scaler_X = ml_scaler.get_scaled_test_data(data_X, model_meta['scaler_param']['scaler_file_path']['XScalerFile']['filePath'], model_meta['scaler_param']['scaler_flag'])
    test_y, scaler_y = ml_scaler.get_scaled_test_data(data_y, model_meta['scaler_param']['scaler_file_path']['yScalerFile']['filePath'], model_meta['scaler_param']['scaler_flag'])

    test_X_array, test_y_array = ML_pipeline.transform_data_by_split_mode(model_meta["transform_param"], test_X, test_y)

    return test_X_array, test_y_array, scaler_X, scaler_y



def ML_test(model_meta, test_X_array, test_y_array, scaler_feature_dict):

    model_info = model_meta['model_info']

    if model_info['model_purpose'] == 'regression':
        preds, trues = ML_pipeline.CLUST_regresstion_test(test_X_array, test_y_array, model_info["train_parameter"], model_info['model_method'], model_info['model_file_path']['modelFile']["filePath"], model_info['model_parameter'])
        df_result = ml_data.get_prediction_df_result(preds, trues, model_meta['scaler_param']['scaler_flag'], scaler_feature_dict['scaler'], scaler_feature_dict['feature_list'], scaler_feature_dict['target'])
        result_metrics =  metrics.calculate_metrics_df(df_result)

    elif model_info['model_purpose'] == 'classification':
        preds, probs, trues, acc = ML_pipeline.clust_classification_test(test_X_array, test_y_array, model_info["train_parameter"], model_info['model_method'], model_info['model_file_path']['modelFile']["filePath"], model_info['model_parameter'])
        result_metrics = classification_report(trues, preds, output_dict = True)
        df_result = ml_data.get_prediction_df_result(preds, trues, model_meta['scaler_param']['scaler_flag'],  scaler_feature_dict['scaler'], scaler_feature_dict['feature_list'], scaler_feature_dict['target'])

    result = {'df_result':df_result, 'result_metrics':result_metrics}

    return result



# df_result = ml_data.get_prediction_df_result(preds, trues, model_meta['scaler_param']['scaler_flag'], scaler, target, target[0])