import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind
from stoc import stoc
import zipfile
import os
import shutil
import statsmodels.api as sm 
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.multicomp import MultiComparison
from itertools import combinations
import scipy.stats as stats

import warnings
warnings.filterwarnings("ignore")

color_p= ["#1984c5", "#22a7f0", "#63bff0", "#a7d5ed", "#e2e2e2", "#e1a692", "#de6e56", "#e14b31", "#c23728"]

# Function definitions
shared_columns = ['idx','dimension', 'rot_type', 'angle', 'mirror', 'wm', 
                  'pair_id', 'obj_id', 'orientation1', 'orientation2', 'image_path_1', 'image_path_2',
                  'marker_id', 'correctAns', 'vivid_response', 'key_resp_vivid_slider_control.keys', 'key_resp_vivid_slider_control.rt', 'participant', 'condition_file']

def get_ans_key(row):
    keys_possible_cols = ['key_resp.keys', 'key_resp_3.keys', 'key_resp_6.keys']
    rt_possible_cols = ['key_resp.rt', 'key_resp_3.rt', 'key_resp_6.rt']
    for key, rt in zip(keys_possible_cols, rt_possible_cols):
        if not pd.isna(row[key]) and row[key] != '':
            return row[key], row[rt]
    return np.nan, np.nan

def get_strategy_response(row):
    if (not pd.isna(row['key_resp_strat_control.keys'])) and (row['key_resp_strat_control.keys'] != 'None') and (row['key_resp_strat_control.keys'] != ''):
        try:    
            strat_resp_list = eval(row['key_resp_strat_control.keys'])
            if len(strat_resp_list) > 0:
                last_key = strat_resp_list[-1]
                if last_key == 'rshift':
                    return 4
                elif last_key == 'slash':
                    return 3
                elif last_key == 'period':
                    return 2
                elif last_key == 'comma':
                    return 1
        except:
            print(row['key_resp_strat_control.keys'])
    return np.nan

def get_vivid_response(row):
    if (not pd.isna(row['key_resp_vivid_slider_control.keys'])) and (row['key_resp_vivid_slider_control.keys'] != 'None') and (row['key_resp_vivid_slider_control.keys'] != ''):
        try:    
            vivid_resp_list = eval(row['key_resp_vivid_slider_control.keys'])
            if len(vivid_resp_list) > 0:
                last_key = vivid_resp_list[-1]
                if last_key == 'rshift':
                    return 4
                elif last_key == 'slash':
                    return 3
                elif last_key == 'period':
                    return 2
                elif last_key == 'comma':
                    return 1
        except:
            print(row['key_resp_vivid_slider_control.keys'])
    return np.nan

def get_block(row):
    if row['dimension'] == '2D':
        if row['wm'] == False:
            return '2D_single'
        elif row['wm'] == True:
            return '2D_wm'
        
    elif row['dimension'] == '3D':
        if row['rot_type'] == 'p':
            if row['wm'] == False:
                return '3Dp_single'
            elif row['wm'] == True:
                return '3Dp_wm'
        elif row['rot_type'] == 'd':
            if row['wm'] == False:
                return '3Dd_single'
            elif row['wm'] == True:
                return '3Dd_wm'

def get_corr(row):
    if row['ans_key'] is np.nan:
        return np.nan
    else:
        if row['correctAns'] == row['ans_key']:
            return 1
        else:
            return 0


def parse_excel(df):
    df_blocks = df[~df['dimension'].isna()]
    df_strat = df[~df['key_resp_strat_control.keys'].isna()]
    df_strat = df_strat[['condition_file', 'key_resp_strat_control.keys', 'key_resp_strat_control.rt']]
    df_blocks.reset_index(drop=True, inplace=True)
    df_blocks['idx'] = df_blocks.index
    df_parsed = pd.DataFrame(columns=shared_columns)
    df_parsed['ans_key'] = np.nan
    df_parsed['rt'] = np.nan
    # iterate over the rows of the dataframe to get the ans keys, corr, rt by get_ans_key function
    for idx, row in df_blocks.iterrows():
        key, rt = get_ans_key(row)
        df_parsed.loc[idx, 'ans_key'] = key
        df_parsed.loc[idx, 'rt'] = rt
        for col in shared_columns:
            df_parsed.loc[idx, col] = row[col]
            
        # replace all 'None' values with np.nan
    df_parsed.replace('None', np.nan, inplace=True)
    df_parsed['vivid_response'] = df_parsed.apply(get_vivid_response, axis=1)

    # fill na values in 'rot_type', 'pair_id', 'orientation1', 'orientation2', 'image_path_2' with not applicable
    for col in ['rot_type', 'pair_id', 'orientation1', 'orientation2', 'image_path_2']:
        df_parsed[col].fillna('na', inplace=True)
        
    df_parsed['block'] = df_parsed.apply(get_block, axis=1)
    df_parsed['corr'] = df_parsed.apply(get_corr, axis=1)
    
    df_parsed = df_parsed.merge(df_strat, on='condition_file', how='left')
    df_parsed['strategy_response'] = df_parsed.apply(get_strategy_response, axis=1)
    
    df_parsed['mini_block'] = df_parsed['condition_file'].apply(lambda x: x.split('/')[1].split('.')[0]) 
    df_parsed.drop(columns=['condition_file'], inplace=True)
    return df_parsed

def parse_vviq(df):
    vviq_score = df['vviq_response'].sum()
    participant = df['participant'].unique()[0]
    tmp_df = pd.DataFrame({'participant': [str(participant)], 'vviq_score': [vviq_score]})
    return tmp_df


# make a new folder 'temp' to store the unzipped files and empty it if it already exists
import os
if os.path.exists('temp'):
    shutil.rmtree('temp')
os.makedirs('temp')

# Streamlit app
st.set_page_config(page_title="PS Behavioral Analysis", layout="wide", page_icon="🧠")
st.title("Problem solving Multi Participant Analysis (May 30 version)")

uploaded_file = st.file_uploader("Upload the zipped file of the data of all participants (max 200MB)", type="zip")

if uploaded_file:
    toc = stoc()
    
    with zipfile.ZipFile(uploaded_file, "r") as z:
        z.extractall("temp")
    
    # get the list of unzipped files
    unzipped_files = os.listdir("temp")
    
    # read all csv files and parse them
    df_all_parsed = pd.DataFrame()
    success_parsed_participant = []
    for file in unzipped_files:
        if file.endswith('.csv'):
            try:
                df = pd.read_csv(f"temp/{file}")
                df_parsed = parse_excel(df)
                df_all_parsed = pd.concat([df_all_parsed, df_parsed], axis=0)
                success_parsed_participant.append(str(df_parsed['participant'].unique()[0]))
            except Exception as e:
                st.write(f"> Error parsing {file}: {e}")
    
    df_all_parsed.reset_index(drop=True, inplace=True)
    df_all_parsed['participant'] = df_all_parsed['participant'].astype(str)
    success_parsed_participant = sorted(success_parsed_participant)
    st.write(f"Successfully parsed participants: {success_parsed_participant}. ", "Total number of participants: ", len(success_parsed_participant))
    
    # delete participants selectbox
    # default is 6, 10, 12, 13 intersected with success_parsed_participant
    default = list(set(['6', '10', '12', '13']).intersection(set(success_parsed_participant)))
    delete_participants = st.multiselect("Delete participants (None by default)", success_parsed_participant, default=default)
    if delete_participants:
        df_all_parsed = df_all_parsed[~df_all_parsed['participant'].isin(delete_participants)]
        st.write(f"Successfully deleted participant(s): {delete_participants}.")
    
    #  Analysis
    
    df_parsed = df_all_parsed.copy()
    st.write("Parsed data:")
    st.dataframe(df_parsed)
    
    # groupby participant, block, wm, rot_type, dimension, angle
    df_agg_analysis = df_all_parsed.groupby(['participant', 'block', 'wm', 'rot_type', 'dimension', 'angle']).agg(
        accuracy=('corr', 'mean'),
        strategy_response=('strategy_response', 'mean'),
        vivid_response=('vivid_response', 'mean'),
        rt=('rt', 'mean')
    ).reset_index().sort_values('participant')
    st.write("Aggregated performance:")
    st.dataframe(df_agg_analysis)
    
    # checkbox to whether or not delete incorrect responses on sidebar
    
    delete_incorrect = st.sidebar.checkbox("Delete incorrect responses for RT analysis")
    if delete_incorrect:
        df_all_parsed_rt = df_all_parsed[df_all_parsed['corr'] == 1]
    else:
        df_all_parsed_rt = df_all_parsed

    # Average Accuracy
    toc.h2("1. Average Accuracy")

    # Broken down by block
    toc.h3("1.1 By Block")
    col1, col2, col3 = st.columns(3)
    
    df_block_accuracy = df_all_parsed.groupby('block')['corr'].agg(['mean', 'std']).reset_index().sort_values('block', ascending=True)
    with col1:
        st.dataframe(df_block_accuracy)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        # sort the df by block
        df_all_parsed_block_sorted = df_all_parsed.sort_values('block')
        sns.barplot(x='block', y='corr', data=df_all_parsed_block_sorted, palette=color_p, ax=ax, capsize=0.1)
        ax.set_xlabel('Block', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Average Accuracy by Block (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    with col3:
        # show all participants' accuracy by block
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_agg_analysis.sort_values('block')
        sns.barplot(data=df_agg_analysis_plot, x='block', y='accuracy', hue='participant', palette= color_p, ax=ax, errorbar=None)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Block', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Accuracy by Block (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    # Broken down by Single vs WM
    toc.h3("1.2 By Single vs WM")
    col1, col2, col3 = st.columns(3)
    df_all_parsed_for_wm = df_all_parsed.copy()
    df_all_parsed_for_wm['wm'] = df_all_parsed_for_wm['wm'].map({True: 'WM', False: 'Single'})
    df_wm_accuracy = df_all_parsed_for_wm.groupby('wm')['corr'].agg(['mean', 'std']).reset_index().sort_values('wm', ascending=True)
    with col1:
        st.dataframe(df_wm_accuracy)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_all_parsed_for_wm = df_all_parsed_for_wm.sort_values('wm')
        sns.barplot(data=df_all_parsed_for_wm, x='wm', y='corr', palette=color_p, ax=ax, capsize=0.05, width=0.4)
        ax.set_xlabel('Single vs WM', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Average Accuracy by Single vs WM (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    with col3:
        # show all participants' accuracy by Single vs WM
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_agg_analysis.sort_values('wm')
        df_agg_analysis_plot.replace({'wm': {True: 'WM', False: 'Single'}}, inplace=True)
        # sns.barplot(data=df_agg_analysis_plot, x='wm', y='accuracy', hue='participant', palette= color_p, ax=ax, errorbar=None, width=0.3)
        sns.lineplot(data=df_agg_analysis_plot, x='wm', y='accuracy', hue='participant',alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.6, y=0.1)

        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Single vs WM', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Accuracy by Single vs WM (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    # Broken down by 2D vs 3D
    toc.h3("1.3 By 2D vs 3D")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        df_2d3d_accuracy = df_all_parsed.groupby('dimension')['corr'].agg(['mean', 'std']).reset_index().sort_values('dimension', ascending=True)
        st.dataframe(df_2d3d_accuracy)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_all_parsed = df_all_parsed.sort_values('dimension')
        sns.barplot(data=df_all_parsed, x='dimension', y='corr', palette=color_p, ax=ax, capsize=0.05, width=0.4)
        ax.set_xlabel('2D vs 3D', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Average Accuracy by 2D vs 3D (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    with col3:
        # show all participants' accuracy by 2D vs 3D
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_agg_analysis.sort_values('dimension')
        # sns.barplot(data=df_agg_analysis_plot, x='dimension', y='accuracy', hue='participant', palette= color_p, ax=ax, errorbar=None, width=0.3)
        sns.lineplot(data=df_agg_analysis_plot, x='dimension', y='accuracy', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.6, y=0.1)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('2D vs 3D', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Accuracy by 2D vs 3D (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    # By angular difference
    toc.h3("1.4 By Angular Difference")
    col1, col2, col3 = st.columns(3)
    with col1:
        df_all_parsed_for_angle = df_all_parsed.copy()
        df_all_parsed_for_angle['angle'] = df_all_parsed_for_angle['angle'].astype(int)
        df_angle_accuracy = df_all_parsed_for_angle.groupby('angle')['corr'].agg(['mean', 'std']).reset_index().sort_values('angle', ascending=True)
        st.dataframe(df_angle_accuracy)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_all_parsed, x='angle', y='corr', palette=color_p, ax=ax, capsize=0.1)
        ax.set_xlabel('Angle', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Average Accuracy by Angular Difference (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    with col3:
        # show all participants' accuracy by angular difference
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_agg_analysis.sort_values(['angle', 'participant'])
        # sns.barplot(data=df_agg_analysis_plot, x='angle', y='accuracy', hue='participant', palette= color_p, ax=ax, errorbar=None)
        sns.lineplot(data=df_agg_analysis_plot, x='angle', y='accuracy', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        # x tick set to 0, 60, 120, 180
        ax.set_xticks([0, 60, 120, 180])
        # margin
        ax.margins(x=0.2, y=0.1)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Angle', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Accuracy by Angular Difference (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    st.write("Separate by wm and single")
    col1, col2, col3 = st.columns(3)
    with col1:
        df_angle_accuracy = df_all_parsed.groupby(['angle', 'wm'])['corr'].agg(['mean', 'std']).reset_index().sort_values('angle', ascending=True)
        df_angle_accuracy['wm'] = df_angle_accuracy['wm'].map({True: 'WM', False: 'Single'})
        st.dataframe(df_angle_accuracy)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_all_parsed.sort_values(['angle', 'participant'])
        df_agg_analysis_plot_single = df_agg_analysis_plot[df_agg_analysis_plot['wm'] == False]
        sns.lineplot(data=df_agg_analysis_plot_single, x='angle', y='corr', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.2, y=0.1)
        ax.set_xticks([0, 60, 120, 180])
        plt.ylim(0.2, 1.2)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Angle', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Accuracy by Angular Difference (Single)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    
    with col3:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_all_parsed.sort_values(['angle', 'participant'])
        df_agg_analysis_plot_wm = df_agg_analysis_plot[df_agg_analysis_plot['wm'] == True]
        sns.lineplot(data=df_agg_analysis_plot_wm, x='angle', y='corr', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.2, y=0.1)
        ax.set_xticks([0, 60, 120, 180])
        plt.ylim(0.2, 1.2)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Angle', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Accuracy by Angular Difference (WM)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)    
        
    # Avg response time
    toc.h2("2. Average Reaction Time")
    
    
    # Broken down by block
    toc.h3("2.1 By Block")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        df_block_rt = df_all_parsed_rt.groupby('block')['rt'].agg(['mean', 'std']).reset_index().sort_values('block', ascending=True)
        st.dataframe(df_block_rt)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_all_parsed_rt_for_block = df_all_parsed_rt.sort_values(['block', 'participant'])
        sns.barplot(data=df_all_parsed_rt_for_block, x='block', y='rt', palette=color_p, ax=ax, capsize=0.1)
        ax.set_xlabel('Block', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('Average RT by Block (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    with col3:
        # show all participants' RT by block
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_all_parsed_rt.sort_values(['block', 'participant'])
        sns.barplot(data=df_agg_analysis_plot, x='block', y='rt', hue='participant', palette= color_p, ax=ax, errorbar=None)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Block', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('RT by Block (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    # Broken down by Single vs WM
    toc.h3("2.2 By Single vs WM")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        df_wm_rt = df_all_parsed_rt.groupby('wm')['rt'].agg(['mean', 'std']).reset_index().sort_values('wm', ascending=True)
        df_wm_rt.replace({'wm': {True: 'WM', False: 'Single'}}, inplace=True)
        st.dataframe(df_wm_rt)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_all_parsed_rt_plot = df_all_parsed_rt.copy()
        df_all_parsed_rt_plot['wm'] = df_all_parsed_rt_plot['wm'].map({True: 'WM', False: 'Single'})
        df_all_parsed_rt_plot = df_all_parsed_rt_plot.sort_values('wm')
        sns.barplot(data=df_all_parsed_rt_plot, x='wm', y='rt', palette=color_p, ax=ax, capsize=0.05, width=0.4)
        ax.set_xlabel('Single vs WM', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('Average RT by Single vs WM (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    with col3:
        # show all participants' RT by Single vs WM
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_all_parsed_rt.sort_values(['wm', 'participant'])
        df_agg_analysis_plot.replace({'wm': {True: 'WM', False: 'Single'}}, inplace=True)
        # sns.barplot(data=df_agg_analysis_plot, x='wm', y='rt', hue='participant', palette= color_p, ax=ax, errorbar=None, width=0.3)
        sns.lineplot(data=df_agg_analysis_plot, x='wm', y='rt', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.6, y=0.1)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Single vs WM', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('RT by Single vs WM (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    # Broken down by 2D vs 3D
    toc.h3("2.3 By 2D vs 3D")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        df_2d3d_rt = df_all_parsed_rt.groupby('dimension')['rt'].agg(['mean', 'std']).reset_index().sort_values('dimension', ascending=True)
        st.dataframe(df_2d3d_rt)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_all_parsed_rt = df_all_parsed_rt.sort_values('dimension')
        sns.barplot(data=df_all_parsed_rt, x='dimension', y='rt', palette=color_p, ax=ax, capsize=0.05, width=0.4)
        ax.set_xlabel('2D vs 3D', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('Average RT by 2D vs 3D (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    with col3:
        # show all participants' RT by 2D vs 3D
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_all_parsed_rt.sort_values(['dimension', 'participant'])
        # sns.barplot(data=df_agg_analysis_plot, x='dimension', y='rt', hue='participant', palette= color_p, ax=ax, errorbar=None, width=0.3)
        sns.lineplot(data=df_agg_analysis_plot, x='dimension', y='rt', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.6, y=0.1)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('2D vs 3D', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('RT by 2D vs 3D (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    # By angular difference
    toc.h3("2.4 By Angular Difference")
    col1, col2, col3 = st.columns(3)
    with col1:
        df_angle_rt = df_all_parsed_rt.groupby('angle')['rt'].agg(['mean', 'std']).reset_index().sort_values('angle', ascending=True)
        st.dataframe(df_angle_rt)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_all_parsed_rt, x='angle', y='rt', palette=color_p, ax=ax, capsize=0.1)
        ax.set_xlabel('Angle', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('Average RT by Angular Difference (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    with col3:
        # show all participants' RT by angular difference
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_all_parsed_rt.sort_values(['angle', 'participant'])
        # sns.barplot(data=df_agg_analysis_plot, x='angle', y='rt', hue='participant', palette= color_p, ax=ax, errorbar=None)
        sns.lineplot(data=df_agg_analysis_plot, x='angle', y='rt', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.2, y=0.1)
        ax.set_xticks([0, 60, 120, 180])
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Angle', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('RT by Angular Difference (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    st.write("Separate by wm and single")
    col1, col2, col3 = st.columns(3)
    with col1:
        df_angle_rt = df_all_parsed_rt.groupby(['angle', 'wm'])['rt'].agg(['mean', 'std']).reset_index().sort_values('angle', ascending=True)
        df_angle_rt['wm'] = df_angle_rt['wm'].map({True: 'WM', False: 'Single'})
        st.dataframe(df_angle_rt)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_all_parsed_rt.sort_values(['angle', 'participant'])
        df_agg_analysis_plot_single = df_agg_analysis_plot[df_agg_analysis_plot['wm'] == False]
        # sns.barplot(data=df_agg_analysis_plot, x='angle', y='rt', hue='participant', palette= color_p, ax=ax, errorbar=None)
        sns.lineplot(data=df_agg_analysis_plot_single, x='angle', y='rt', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.2, y=0.1)
        ax.set_xticks([0, 60, 120, 180])
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Angle', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.ylim(0.2, 8)
        plt.title('RT by Angular Difference (Single)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    with col3:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_agg_analysis_plot = df_all_parsed_rt.sort_values(['angle', 'participant'])
        df_agg_analysis_plot_wm = df_agg_analysis_plot[df_agg_analysis_plot['wm'] == True]
        # sns.barplot(data=df_agg_analysis_plot, x='angle', y='rt', hue='participant', palette= color_p, ax=ax, errorbar=None)
        sns.lineplot(data=df_agg_analysis_plot_wm, x='angle', y='rt', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.2, y=0.1)
        ax.set_xticks([0, 60, 120, 180])
        plt.ylim(0.2, 8)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Angle', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('RT by Angular Difference (WM)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    # By correct vs incorrect
    toc.h3("2.5 By Correct vs Incorrect")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        df_corr_rt = df_all_parsed.groupby('corr')['rt'].agg(['mean', 'std']).reset_index().sort_values('corr', ascending=True)
        df_corr_rt['corr'] = df_corr_rt['corr'].map({1: 'Correct', 0: 'Incorrect'}) 
        st.dataframe(df_corr_rt)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_all_parsed_cor_incor = df_all_parsed.copy()
        df_all_parsed_cor_incor['corr'] = df_all_parsed_cor_incor['corr'].map({1: 'Correct', 0: 'Incorrect'})
        sns.barplot(data=df_all_parsed_cor_incor, x='corr', y='rt', palette=color_p, ax=ax, capsize=0.05, width=0.4)
        # add error bars
        ax.set_xlabel('Correct vs Incorrect', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('Average RT by Correct vs Incorrect (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    with col3:
        df_corr_rt_participant = df_all_parsed.groupby(['participant', 'corr'])['rt'].mean().reset_index().sort_values('participant')
        df_corr_rt_participant['corr'] = df_corr_rt_participant['corr'].map({1: 'Correct', 0: 'Incorrect'})
        df_corr_rt_participant.sort_values('corr', inplace=True)
        # show all participants' RT by correct vs incorrect
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        # sns.barplot(data=df_corr_rt_participant, x='corr', y='rt', hue='participant', palette= color_p, ax=ax, errorbar=None, width=0.3)
        sns.lineplot(data=df_corr_rt_participant, x='corr', y='rt', hue='participant', alpha = 0.9, palette=color_p, ax=ax, err_style=None, marker='o', markersize=10, linewidth=3)
        ax.margins(x=0.6, y=0.1)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Correct vs Incorrect', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('RT by Correct vs Incorrect (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
                
    # Performance Over Time
    toc.h2("3. Performance Over Time")
    
    col1, col2 = st.columns(2)
    with col1:  
        # Accuracy
        toc.h3("3.1 Accuracy")
        df_all_parsed = df_all_parsed.sort_values(['participant', 'idx'])
        # running average accuracy over idx 
        df_all_parsed['running_avg_accuracy'] = df_all_parsed.groupby('participant')['corr'].transform(lambda x: x.expanding().mean())
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        df_all_parsed = df_all_parsed.sort_values(['participant', 'idx'])
        sns.lineplot(data=df_all_parsed, x='idx', y='running_avg_accuracy', hue='participant', palette=color_p, ax=ax)
        ax.set_xlabel('Index', fontsize=14)
        ax.set_ylabel('Running Average Accuracy', fontsize=14)
        plt.title('Running Average Accuracy Over Time (by participant)')
        
        # # color background for each block
        # for idx, block in enumerate(df_all_parsed['mini_block'].unique()):
        #     block_idx = df_all_parsed[df_all_parsed['mini_block'] == block]['idx']
        #     ax.axvspan(block_idx.min(), block_idx.max(), alpha=0.1, color=color_p[idx])
        #     # add block label in the bottom
        #     ax.text(block_idx.mean(), df_all_parsed['running_avg_accuracy'].min(), block, ha='center', va='center', fontsize=8, color='black')
            
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
              
        sns.despine()
        st.pyplot(fig)
        
    with col2:
        # RT
        toc.h3("3.2 Reaction Time")
        # running average RT over idx 
        df_all_parsed['running_avg_rt'] = df_all_parsed.groupby('participant')['rt'].transform(lambda x: x.expanding().mean())
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.lineplot(data=df_all_parsed, x='idx', y='running_avg_rt', hue='participant', palette=color_p, ax=ax)
        ax.set_xlabel('Index', fontsize=14)
        ax.set_ylabel('Running Average RT', fontsize=14)
        plt.title('Running Average RT Over Time (by participant)')
        
        # color background for each block
        # for idx, block in enumerate(df_all_parsed['block'].unique()):
        #     block_idx = df_all_parsed[df_all_parsed['block'] == block]['idx']
        #     ax.axvspan(block_idx.min(), block_idx.max(), alpha=0.1, color=color_p[idx])
        #     # add block label in the bottom
        #     ax.text(block_idx.mean(), df_all_parsed['running_avg_rt'].min(), block, ha='center', va='center', fontsize=8, color='black')
            
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
              
        sns.despine()
        st.pyplot(fig)
        
    # strategy response vs performance
    toc.h2("4. Mini-block Strategy vs Performance")
    
    df_block_strat = df_all_parsed[['participant', 'mini_block', 'strategy_response']].drop_duplicates()
    col1, col2 = st.columns(2)
    with col1:
        st.write("Count of strategy responses of mini-blcoks:")
        st.write(df_block_strat['strategy_response'].value_counts().reset_index().sort_values('strategy_response').reset_index(drop=True))
        
    with col2:
        st.write("Count of strategy responses by participants:")
        df_strategy_cnt_pivot = df_block_strat.pivot_table(index='participant', columns='strategy_response', values='mini_block', aggfunc='count').reset_index().fillna(0)
        st.dataframe(df_strategy_cnt_pivot)
    
    # Accuracy vs Strategy Response
    toc.h3("4.1 Accuracy")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        df_all_parsed_for_strat = df_all_parsed.copy()
        df_strategy_accuracy = df_all_parsed_for_strat.groupby('strategy_response')['corr'].agg(['mean', 'std']).reset_index().sort_values('strategy_response', ascending=True)
        st.dataframe(df_strategy_accuracy)
        
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_all_parsed, x='strategy_response', y='corr', palette=color_p, ax=ax, capsize=0.1)
        ax.set_xlabel('Strategy Response', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Average Accuracy by Strategy Response (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    with col3:
        # group by participant, strategy_response and get the accuracy
        df_strategy_accuracy_participant = df_all_parsed.groupby(['participant', 'strategy_response'])['corr'].mean().reset_index().sort_values('participant')
        # plot
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_strategy_accuracy_participant, x='strategy_response', y='corr', hue='participant', palette= color_p, ax=ax, errorbar=None)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Strategy Response', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Accuracy by Strategy Response (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)

        
    # RT vs Strategy Response
    toc.h3("4.2 Reaction Time")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        df_strategy_rt = df_all_parsed_rt.groupby('strategy_response')['rt'].agg(['mean', 'std']).reset_index().sort_values('strategy_response', ascending=True)
        st.dataframe(df_strategy_rt)
    
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_all_parsed_rt, x='strategy_response', y='rt', palette=color_p, ax=ax, capsize=0.1)
        ax.set_xlabel('Strategy Response', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('Average RT by Strategy Response (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    
    with col3:
        # group by participant, strategy_response and get the RT
        df_strategy_rt_participant = df_all_parsed_rt.groupby(['participant', 'strategy_response'])['rt'].mean().reset_index().sort_values('participant')
        # plot
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_strategy_rt_participant, x='strategy_response', y='rt', hue='participant', palette= color_p, ax=ax, errorbar=None)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Strategy Response', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('RT by Strategy Response (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    # Vividness vs Performance
    toc.h2("5. Vividness vs Performance")
    
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("Count of vividness responses:")
        st.write(df_all_parsed['vivid_response'].value_counts().reset_index().sort_values('vivid_response').reset_index(drop=True))
    
    with col2:
        st.write("Count of vividness responses by participants:")
        df_vivid_cnt_pivot = df_all_parsed.pivot_table(index='participant', columns='vivid_response', values='idx', aggfunc='count').reset_index().fillna(0)
        st.dataframe(df_vivid_cnt_pivot)
        
    # Accuracy vs Vivid Response
    toc.h3("5.1 Accuracy")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        df_all_parsed_for_vivid = df_all_parsed.copy()
        df_vivid_accuracy = df_all_parsed_for_vivid.groupby('vivid_response')['corr'].agg(['mean', 'std']).reset_index().sort_values('vivid_response', ascending=True)
        st.dataframe(df_vivid_accuracy)
        
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_all_parsed, x='vivid_response', y='corr', palette=color_p, ax=ax, capsize=0.1)
        ax.set_xlabel('Vivid Response', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Average Accuracy by Vivid Response (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    with col3:
        # group by participant, vivid_response and get the accuracy
        df_vivid_accuracy_participant = df_all_parsed.groupby(['participant', 'vivid_response'])['corr'].mean().reset_index().sort_values('participant')
        # plot
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_vivid_accuracy_participant, x='vivid_response', y='corr', hue='participant', palette= color_p, ax=ax, errorbar=None)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Vivid Response', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        plt.title('Accuracy by Vivid Response (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    # RT vs Vivid Response
    toc.h3("5.2 Reaction Time")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        df_vivid_rt = df_all_parsed_rt.groupby('vivid_response')['rt'].agg(['mean', 'std']).reset_index().sort_values('vivid_response', ascending=True)
        st.dataframe(df_vivid_rt)
        
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_all_parsed_rt, x='vivid_response', y='rt', palette=color_p, ax=ax, capsize=0.1)
        ax.set_xlabel('Vivid Response', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('Average RT by Vivid Response (agg over participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    with col3:
        # group by participant, vivid_response and get the RT
        df_vivid_rt_participant = df_all_parsed_rt.groupby(['participant', 'vivid_response'])['rt'].mean().reset_index().sort_values('participant')
        # plot
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_vivid_rt_participant, x='vivid_response', y='rt', hue='participant', palette= color_p, ax=ax, errorbar=None)
        plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
        ax.set_xlabel('Vivid Response', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        plt.title('RT by Vivid Response (breakdown by all participants)')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    
    
    toc.h2("6. ANOVA of Accuracy and RT")
    
    # tick box to delete 3Dd_wm block
    if st.sidebar.checkbox("Delete 3Dd_wm block for ANOVA"):
        df_all_parsed_3dd_cond = df_all_parsed[df_all_parsed['block'] != '3Dd_wm']
        df_all_parsed_3dd_cond_rt = df_all_parsed_rt[df_all_parsed_rt['block'] != '3Dd_wm']
    else:
        df_all_parsed_3dd_cond = df_all_parsed.copy()
        df_all_parsed_3dd_cond_rt = df_all_parsed_rt.copy()
    
    
    col1, col2 = st.columns(2)
    with col1: 
        # Accuracy
        toc.h3("6.1 Accuracy")
        # ANOVA
        df_all_parsed_for_anova = df_all_parsed_3dd_cond.copy()[['corr', 'wm', 'dimension', 'angle', 'block']]
        df_all_parsed_for_anova['corr'] = df_all_parsed_for_anova['corr'].astype(float)
        df_all_parsed_for_anova.dropna(inplace=True)
        df_all_parsed_for_anova['angle'] = df_all_parsed_for_anova['angle'].astype('str') + 'deg'
        df_all_parsed_for_anova['angle'] = df_all_parsed_for_anova['angle'].astype('category')
        df_all_parsed_for_anova['wm'] = df_all_parsed_for_anova['wm'].map({True: 'WM', False: 'Single'})
        df_all_parsed_for_anova['wm'] = df_all_parsed_for_anova['wm'].astype('category')
        df_all_parsed_for_anova['dimension'] = df_all_parsed_for_anova['dimension'].astype('category')
        df_all_parsed_for_anova['block'] = df_all_parsed_for_anova['block'].astype('category')
        
        # anova multi-select
        anova_factors = st.multiselect("Select variables for ANOVA", ['wm', 'dimension', 'angle', 'block'], key = 'anova_factors', default= ['wm', 'dimension', 'angle'])
        
        # Generate all possible combinations of variables
        combs = sum([list(map(list, combinations(anova_factors, i))) for i in range(1, len(anova_factors) + 1)], [])

        # Generate the formula string
        formula = 'corr ~ ' + ' + '.join(['C(' + '):C('.join(c) + ')' for c in combs])
        anova_acc = ols(formula, data=df_all_parsed_for_anova).fit()
        anova_table = sm.stats.anova_lm(anova_acc, typ=2)
        st.write(anova_table)
        
        st.write("Post-hoc test:")
        factors = st.multiselect("Select factors for post-hoc test", anova_factors, key = 'factors', default= anova_factors)
        # multi compare
        tmp = df_all_parsed_for_anova[factors]
        tmp['group_label'] = tmp.apply(lambda x: '_'.join(x), axis=1)
        df_all_parsed_for_anova['group_label'] = tmp['group_label']
        mc = MultiComparison(df_all_parsed_for_anova['corr'], df_all_parsed_for_anova['group_label'])
        mc_results = mc.tukeyhsd()
        st.write(mc_results)
        
        # 2 way table to see the mean accuracy
        # selectbox for 2 factors
        anova_viz_fac1 = st.selectbox("Select factor 1", anova_factors, key = 'anova_viz_fac1', index=0)
        anova_viz_fac2 = st.selectbox("Select factor 2", anova_factors, key = 'anova_viz_fac2', index=1)
        if anova_viz_fac1 == anova_viz_fac2:
            st.write("Please select different factors for 2-way table")
        else:
            df_acc_2way = df_all_parsed_for_anova.groupby([anova_viz_fac1, anova_viz_fac2])['corr'].mean().reset_index()
            df_acc_2way.sort_values([anova_viz_fac1, anova_viz_fac2], inplace=True)
            df_acc_2way_pivot = df_acc_2way.pivot_table(index=anova_viz_fac1, columns=anova_viz_fac2, values='corr').reset_index()
            st.write("Mean Accuracy by 2 factors:")
            st.dataframe(df_acc_2way_pivot)
            # plot 2 way table as line plot x-axis: factor1, hue: factor2, y: accuracy
            fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
            sns.lineplot(data=df_acc_2way, x=anova_viz_fac1, y='corr', hue=anova_viz_fac2, palette=color_p, ax=ax, marker='o', markersize=10, linewidth=3)
            ax.set_xlabel(anova_viz_fac1, fontsize=14)
            ax.set_ylabel('Accuracy', fontsize=14)
            # margin
            ax.margins(x=0.6, y=0.1)
            plt.title('Accuracy by 2 factors')
            plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
            sns.despine()
            st.pyplot(fig)
            
      
    with col2:
        # RT
        toc.h3("6.2 Reaction Time")
        # ANOVA
        df_all_parsed_rt_for_anova = df_all_parsed_3dd_cond_rt.copy()[['rt', 'wm', 'dimension', 'angle', 'block']]
        df_all_parsed_rt_for_anova.dropna(inplace=True)
        df_all_parsed_rt_for_anova['angle'] = df_all_parsed_rt_for_anova['angle'].astype('str') + 'deg'
        df_all_parsed_rt_for_anova['angle'] = df_all_parsed_rt_for_anova['angle'].astype('category')
        df_all_parsed_rt_for_anova['wm'] = df_all_parsed_rt_for_anova['wm'].map({True: 'WM', False: 'Single'})
        df_all_parsed_rt_for_anova['wm'] = df_all_parsed_rt_for_anova['wm'].astype('category')
        df_all_parsed_rt_for_anova['dimension'] = df_all_parsed_rt_for_anova['dimension'].astype('category')
        df_all_parsed_rt_for_anova['block'] = df_all_parsed_rt_for_anova['block'].astype('category')
        
        # anova multi-select
        anova_factors_rt = st.multiselect("Select variables for ANOVA", ['wm', 'dimension', 'angle', 'block'], key = 'anova_factors_rt', default= ['wm', 'dimension', 'angle'])
        
        # Generate all possible combinations of variables
        combs_rt = sum([list(map(list, combinations(anova_factors_rt, i))) for i in range(1, len(anova_factors_rt) + 1)], [])
        formula_rt = 'rt ~ ' + ' + '.join(['C(' + '):C('.join(c) + ')' for c in combs_rt])
        
        two_way_anova_rt = ols(formula_rt, data=df_all_parsed_rt_for_anova).fit()
        anova_table_rt = sm.stats.anova_lm(two_way_anova_rt, typ=2)
        st.write(anova_table_rt)
        
        # post-hoc test
        st.write("Post-hoc test:")
        # selectbox for factor
        factors = st.multiselect("Select factor for post-hoc test", anova_factors_rt, key = 'factors_rt', default= anova_factors_rt)
        # multi compare
        tmp = df_all_parsed_rt_for_anova[factors]
        tmp['group_label'] = tmp.apply(lambda x: '_'.join(x), axis=1)
        df_all_parsed_rt_for_anova['group_label'] = tmp['group_label']
        mc_rt = MultiComparison(df_all_parsed_rt_for_anova['rt'], df_all_parsed_rt_for_anova['group_label'])
        mc_results_rt = mc_rt.tukeyhsd()
        st.write(mc_results_rt)
        
        # 2 way table to see the mean RT
        # selectbox for 2 factors
        anova_viz_fac1_rt = st.selectbox("Select factor 1", anova_factors_rt, key = 'anova_viz_fac1_rt', index=0)
        anova_viz_fac2_rt = st.selectbox("Select factor 2", anova_factors_rt, key = 'anova_viz_fac2_rt', index=1)
        if anova_viz_fac1_rt == anova_viz_fac2_rt:
            st.write("Please select different factors for 2-way table")
        else:
            df_rt_2way = df_all_parsed_rt_for_anova.groupby([anova_viz_fac1_rt, anova_viz_fac2_rt])['rt'].mean().reset_index()
            df_rt_2way = df_rt_2way.sort_values([anova_viz_fac1_rt, anova_viz_fac2_rt])
            df_rt_2way_pivot = df_rt_2way.pivot_table(index=anova_viz_fac1_rt, columns=anova_viz_fac2_rt, values='rt').reset_index()
            st.write("Mean RT by 2 factors:")
            st.dataframe(df_rt_2way_pivot)
            # plot 2 way table as line plot x-axis: factor1, hue: factor2, y: RT
            fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
            sns.lineplot(data=df_rt_2way, x=anova_viz_fac1_rt, y='rt', hue=anova_viz_fac2_rt, palette=color_p, ax=ax, marker='o', markersize=10, linewidth=3)
            ax.set_xlabel(anova_viz_fac1_rt, fontsize=14)
            ax.set_ylabel('RT', fontsize=14)
            # margin
            ax.margins(x=0.6, y=0.1)
            plt.title('RT by 2 factors')
            plt.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0.)
            sns.despine()
            st.pyplot(fig)
            
    toc.h2("7. TBT Vividness vs Performance")
    
    # reported vividness distribution
    toc.h3("7.0 Vividness Distribution")
    col1, col2 = st.columns(2)
    with col1:
        # number of vividness responses at every level
        st.write("Count of vividness responses:")
        st.write(df_all_parsed['vivid_response'].value_counts().reset_index().sort_values('vivid_response').reset_index(drop=True))
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        # bar plot of vividness distribution
        vivid_cnt = df_all_parsed['vivid_response'].value_counts().reset_index().sort_values('vivid_response').reset_index(drop=True)
        sns.barplot(data=vivid_cnt, x='vivid_response', y='count', palette=color_p, ax=ax)
        ax.set_xlabel('Vividness', fontsize=14)
        ax.set_ylabel('Count', fontsize=14)
        plt.title('Vividness Distribution')
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    
    col1, col2 = st.columns(2)
    # vividness vs accuracy
    with col1:
        toc.h3("7.1 Accuracy")
        # correlation between vividness and accuracy
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_all_parsed, x='vivid_response', y='corr', palette=color_p, ax=ax, capsize=0.1)
        # sns.stripplot(data=df_all_parsed, x='vivid_response', y='corr', ax=ax, palette=color_p, 
        ax.set_xlabel('Vividness', fontsize=14)
        ax.set_ylabel('Accuracy', fontsize=14)
        
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
        
    with col2:
        # vividness vs rt
        toc.h3("7.2 Reaction Time")
        # correlation between vividness and rt
        fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
        sns.barplot(data=df_all_parsed_rt, x='vivid_response', y='rt', palette=color_p, ax=ax, capsize=0.1)
        ax.set_xlabel('Vividness', fontsize=14)
        ax.set_ylabel('RT', fontsize=14)
        
        # remove top and right borders
        sns.despine()
        st.pyplot(fig)
    
    
    # Optinal VVIQ - behavior analysis
    toc.h2("8. Optional VVIQ - Behavior Analysis")
    # Upload VVIQ data
    uploaded_file_vviq = st.file_uploader("Please zip the VVIQ data and upload here", type=["zip"])
    if uploaded_file_vviq:
        with zipfile.ZipFile(uploaded_file_vviq, "r") as z:
            z.extractall("vviq")
        
        # get the list of unzipped files
        unzipped_vviq_files = os.listdir("vviq")
        
        # read all csv files and parse them
        df_vviq = pd.DataFrame()
        success_vviq_parsed_participant = []
        for file in unzipped_vviq_files:
            if file.endswith('.csv'):
                try:
                    df = pd.read_csv(f"vviq/{file}")
                    df_vviq = pd.concat([df_vviq, parse_vviq(df)], axis=0)
                    success_vviq_parsed_participant.append(str(df['participant'].unique()[0]))
                except:
                    st.write(f"Error parsing {file}")
        
        df_vviq.sort_values('participant', inplace=True)
        st.write(f"Successfully parsed the vviq data of participants: {success_vviq_parsed_participant}")
        st.write("VVIQ scores:")
        st.dataframe(df_vviq)
        
        st.write("Merging VVIQ data with the main data...")
        # check set difference if there are any participants in the main data but not in the vviq data
        main_participants = set(df_all_parsed['participant'].unique())
        vviq_participants = set(df_vviq['participant'].unique())
        diff = main_participants.difference(vviq_participants)
        if diff:
            st.write(f"Participants in the main data but not in the VVIQ data: {diff}")
        else:
            st.write("All participants in the main data have VVIQ data.")
            
        # merge the vviq data with the main data
        df_all_parsed = pd.merge(df_all_parsed, df_vviq, on='participant', how='left')
        
        # VVIQ vs Performance
        # Accuracy vs VVIQ
        toc.h3("8.1 Accuracy vs VVIQ")
        
        # scatter plot of vviq and average accuracy, also breakdown by block
        col1, col2, col3 = st.columns(3)
        with col1:
            df_vviq_acc = df_all_parsed.groupby('participant')['corr'].mean().reset_index()
            df_vviq_acc = pd.merge(df_vviq_acc, df_vviq, on='participant', how='left')
            fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
            sns.regplot(data=df_vviq_acc, x='vviq_score', y='corr', ax=ax, scatter_kws={'s': 15})
            ax.set_xlabel('VVIQ', fontsize=14)
            ax.set_ylabel('Accuracy', fontsize=14)
            plt.title('Accuracy vs VVIQ')
            # remove top and right borders
            sns.despine()
            # plot spearman r in the plot
            r, p = stats.spearmanr(df_vviq_acc['vviq_score'], df_vviq_acc['corr'])
            ax.text(0.75, 0.25, f"r = {r:.2f},\np = {p:.2f}", transform=ax.transAxes, fontsize=13, verticalalignment='top')
            st.pyplot(fig)
        with col2:
            # WM
            df_vviq_acc_wm = df_all_parsed[df_all_parsed['wm'] == True].groupby('participant')['corr'].mean().reset_index()
            df_vviq_acc_wm = pd.merge(df_vviq_acc_wm, df_vviq, on='participant', how='left')
            fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
            sns.regplot(data=df_vviq_acc_wm, x='vviq_score', y='corr', ax=ax, scatter_kws={'s': 15})
            ax.set_xlabel('VVIQ', fontsize=14)
            ax.set_ylabel('Accuracy', fontsize=14)
            plt.title('Accuracy vs VVIQ (WM)')
            # remove top and right borders
            sns.despine()
            # plot spearman r in the plot
            r, p = stats.spearmanr(df_vviq_acc_wm['vviq_score'], df_vviq_acc_wm['corr'])
            ax.text(0.75, 0.25, f"r = {r:.2f},\np = {p:.2f}", transform=ax.transAxes, fontsize=13, verticalalignment='top')
            st.pyplot(fig)
        with col3:
            # Single
            df_vviq_acc_single = df_all_parsed[df_all_parsed['wm'] == False].groupby('participant')['corr'].mean().reset_index()
            df_vviq_acc_single = pd.merge(df_vviq_acc_single, df_vviq, on='participant', how='left')
            fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
            sns.regplot(data=df_vviq_acc_single, x='vviq_score', y='corr', ax=ax, scatter_kws={'s':15})
            ax.set_xlabel('VVIQ', fontsize=14)
            ax.set_ylabel('Accuracy', fontsize=14)
            plt.title('Accuracy vs VVIQ (Single)')
            # remove top and right borders
            sns.despine()
            # plot spearman r in the plot
            r, p = stats.spearmanr(df_vviq_acc_single['vviq_score'], df_vviq_acc_single['corr'])
            ax.text(0.75, 0.25, f"r = {r:.2f},\np = {p:.2f}", transform=ax.transAxes, fontsize=13, verticalalignment='top')
            st.pyplot(fig)
        
        # Accuracy vs VVIQ by block
        # facet grid plot in seaborn
        df_vviq_acc_block = df_all_parsed.groupby(['participant', 'block'])['corr'].mean().reset_index()
        df_vviq_acc_block = pd.merge(df_vviq_acc_block, df_vviq, on='participant', how='left')
        
        g = sns.FacetGrid(df_vviq_acc_block, col='block', col_wrap=5, height=3.5, aspect=1)
        # set the dpi for better resolution
        g.fig.set_dpi(300)
        g.map_dataframe(sns.regplot, x='vviq_score', y='corr', scatter_kws={'s': 15})
        # add spearman r in the plot
        for ax in g.axes.flat:
            block = ax.get_title().split('=')[1].strip()
            df_block = df_vviq_acc_block[df_vviq_acc_block['block'] == block]
            r, p = stats.spearmanr(df_block['vviq_score'], df_block['corr'])
            ax.text(0.7, 0.25, f"r = {r:.2f},\np = {p:.2f}", transform=ax.transAxes, fontsize=12, verticalalignment='top')
        g.set_axis_labels('VVIQ', 'Accuracy')
        st.pyplot(g)
        
        st.write("* r: Spearman correlation coefficient, p: p-value")
        # RT vs VVIQ
        toc.h3("8.2 Reaction Time vs VVIQ")
        
        # scatter plot of vviq and average rt, also breakdown by block
        col1, col2, col3 = st.columns(3)
        
        with col1:
            df_vviq_rt = df_all_parsed_rt.groupby('participant')['rt'].mean().reset_index()
            df_vviq_rt = pd.merge(df_vviq_rt, df_vviq, on='participant', how='left')
            fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
            sns.regplot(data=df_vviq_rt, x='vviq_score', y='rt', ax=ax, scatter_kws={'s': 15})
            ax.set_xlabel('VVIQ', fontsize=14)
            ax.set_ylabel('RT', fontsize=14)
            plt.title('RT vs VVIQ')
            # remove top and right borders
            sns.despine()
            # plot spearman r in the plot
            r, p = stats.spearmanr(df_vviq_rt['vviq_score'], df_vviq_rt['rt'])
            ax.text(0.75, 0.8, f"r = {r:.2f},\np = {p:.2f}", transform=ax.transAxes, fontsize=13, verticalalignment='top')
            st.pyplot(fig)
        with col2:
            # WM
            df_vviq_rt_wm = df_all_parsed_rt[df_all_parsed_rt['wm'] == True].groupby('participant')['rt'].mean().reset_index()
            df_vviq_rt_wm = pd.merge(df_vviq_rt_wm, df_vviq, on='participant', how='left')
            fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
            sns.regplot(data=df_vviq_rt_wm, x='vviq_score', y='rt', ax=ax, scatter_kws={'s': 15})
            ax.set_xlabel('VVIQ', fontsize=14)
            ax.set_ylabel('RT', fontsize=14)
            plt.title('RT vs VVIQ (WM)')
            # remove top and right borders
            sns.despine()
            # plot spearman r in the plot
            r, p = stats.pearsonr(df_vviq_rt_wm['vviq_score'], df_vviq_rt_wm['rt'])
            ax.text(0.75, 0.8, f"r = {r:.2f},\np = {p:.2f}", transform=ax.transAxes, fontsize=13, verticalalignment='top')
            st.pyplot(fig)
        with col3:
            # Single
            df_vviq_rt_single = df_all_parsed_rt[df_all_parsed_rt['wm'] == False].groupby('participant')['rt'].mean().reset_index()
            df_vviq_rt_single = pd.merge(df_vviq_rt_single, df_vviq, on='participant', how='left')
            fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
            sns.regplot(data=df_vviq_rt_single, x='vviq_score', y='rt', ax=ax, scatter_kws={'s': 15})
            ax.set_xlabel('VVIQ', fontsize=14)
            ax.set_ylabel('RT', fontsize=14)
            plt.title('RT vs VVIQ (Single)')
            # remove top and right borders
            sns.despine()
            # plot spearman r in the plot
            r, p = stats.spearmanr(df_vviq_rt_single['vviq_score'], df_vviq_rt_single['rt'])
            ax.text(0.75, 0.8, f"r = {r:.2f},\np = {p:.2f}", transform=ax.transAxes, fontsize=13, verticalalignment='top')
            st.pyplot(fig)
            
        # RT vs VVIQ by block
        # facet grid plot in seaborn
        df_vviq_rt_block = df_all_parsed_rt.groupby(['participant', 'block'])['rt'].mean().reset_index()
        df_vviq_rt_block = pd.merge(df_vviq_rt_block, df_vviq, on='participant', how='left')
        
        g = sns.FacetGrid(df_vviq_rt_block, col='block', col_wrap=5, height=3.5, aspect=1)
        # set the dpi for better resolution
        g.fig.set_dpi(300)
        g.map_dataframe(sns.regplot, x='vviq_score', y='rt', scatter_kws={'s': 15})
        # add spearman r in the plot
        for ax in g.axes.flat:
            block = ax.get_title().split('=')[1].strip()
            df_block = df_vviq_rt_block[df_vviq_rt_block['block'] == block]
            r, p = stats.spearmanr(df_block['vviq_score'], df_block['rt'])
            ax.text(0.7, 0.8, f"r = {r:.2f},\np = {p:.2f}", transform=ax.transAxes, fontsize=12, verticalalignment='top')
        g.set_axis_labels('VVIQ', 'RT')
        st.pyplot(g)
        st.write("* r: Spearman correlation coefficient, p: p-value")
            
    toc.toc()
    