import streamlit as st
import pandas as pd
import json
import func

# タイトルを表示
st.title("2-gram住所検索")
st.write("CSVファイルをアップロードすると転置インデックスファイルの生成を開始します")

# 状態を保持する変数の初期化
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'address_string_list' not in st.session_state:
    st.session_state.address_string_list = []
if 'inverted_index' not in st.session_state:
    st.session_state.inverted_index = {}
if 'inverted_index_json' not in st.session_state:
    st.session_state.inverted_index_json = None

# ファイルアップロード状態の管理するフラグを定義
if 'csv_processed' not in st.session_state:
    st.session_state.csv_processed = False
if 'json_loaded' not in st.session_state:
    st.session_state.json_loaded = False

# ファイルのアップロードとエンコード指定
uploaded_csv = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])
encoode = st.text_input("ファイルのエンコーディング", value="cp932")

if uploaded_csv and encoode and not st.session_state.csv_processed:
    try:
        # CSVファイルをデータフレームとして読み込む
        st.session_state.df = pd.read_csv(uploaded_csv, encoding=encoode, low_memory=False)
        
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

    with st.spinner("転置インデックスファイルを作成中..."):
        # dfを検索用の文字列のリストに変換する
        st.session_state.address_string_list = func.extract_address_string(st.session_state.df)
        # 転置インデックスのJSONファイルを作成
        st.session_state.inverted_index_json = func.generate_inverted_index_json(st.session_state.address_string_list)
    
    st.session_state.csv_processed = True  # 処理完了フラグを設定

if st.session_state.csv_processed:
    st.success("転置インデックスファイルの作成が完了しました")
   
    # 作成した転置インデックスファイルのダウンロードボタン
    st.download_button(
        label="ファイルをダウンロード",
        data=st.session_state.inverted_index_json,
        file_name="invertedIndex.json",
        mime="application/json"
    )

    # JSONファイルの文字列から直接辞書を作成
    if not st.session_state.json_loaded:
        try:
            # 作成作成された転置インデックスのJSONファイルを読み込む
            st.session_state.inverted_index = json.loads(st.session_state.inverted_index_json)
            st.session_state.json_loaded = True # JSONファイル読み込み完了フラグを設定
        except Exception as e:
            st.error(f"転置インデックスの処理中にエラーが発生しました: {e}")

    if st.session_state.json_loaded:
        search_q = st.text_input(label="検索語を入力してください")
        if len(search_q) > 1:
            target_index_list = []

            try:
                target_index_list = func.search_address(st.session_state.inverted_index, search_q)
            except KeyError:
                # 転置インデックス内に一致するトークンがない場合のkeyErrorハンドル
                target_index_list = []
            
            # 検索キューの単語と完全一致する結果に絞る
            filtered_index_list = func.filter_index(st.session_state.address_string_list, target_index_list, search_q)
            
            output_list = func.prepare_output_string_list(st.session_state.df, filtered_index_list)

            st.title("検索結果：{}件".format(len(output_list)))
            # 結果を出力
            for output in output_list:
                st.write(output)
    

