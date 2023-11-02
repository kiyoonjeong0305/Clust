import pandas as pd
import sys
sys.path.append("../")
sys.path.append("../../")

from Clust.clust.analysis import dataAnalysis

class DataSetAnalysis():
    def get_multiple_max_correlation_value_table_with_lag(self, analysis_param, df_set):
        """
        Description
        - lag를 적용하여 상관관계를 구한 후 가장 높은 값의 value table 추출

        Args:
            analysis_param (_Dictionary_)
            df_set (_Dictionary(pd.dataFrame)_)

        Returns:
            _pd.dataFrame_ : max_correlation_value_timelag

        """
        column_list = next(iter((df_set.items())))[1].columns
        max_correlation_value_timelag = pd.DataFrame(index = column_list)
        
        #feature_key = analysis_param['feature_key'] #사용하는 값인지요?
        #lag_number = analysis_param['lag_number'] #사용하는 값인지요?

        for df_name in df_set.keys():
            data = df_set[df_name]
            
            #-------------------------------------------------
            max_position_table = dataAnalysis.DataAnalysis().get_max_correlation_table_with_lag(analysis_param, data)
            max_correlation_value_timelag[df_name] = max_position_table['value']

        return max_correlation_value_timelag
    
    def get_multiple_max_correlation_index_table_with_lag(self, analysis_param, df_set):
        """
        Description

        Args:
            analysis_param(Dictionary)
            df_set(Dictionary)

        Returns:
            pd.dataFrame : max_correlation_index_timelag
        
        """
        column_list = next(iter((df_set.items())))[1].columns
        max_correlation_index_timelag = pd.DataFrame(index = column_list)
        feature_key = analysis_param['feature_key'] #사용하는 값인지요?
        lag_number = analysis_param['lag_number'] #사용하는 값인지요?
        
        for df_name in df_set.keys():
            data = df_set[df_name]
            #################################################
            max_position_table = dataAnalysis.DataAnalysis().get_max_correlation_table_with_lag(analysis_param, data)
            max_correlation_index_timelag[df_name]=max_position_table['index']

        return max_correlation_index_timelag
    
    ####Analysis #########################################################
    