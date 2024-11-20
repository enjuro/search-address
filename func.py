import json
from collections import defaultdict

# dfの必要な列名のみ定数として定義
SEARCH_TARGET_COLUMNS = ["都道府県", "市区町村", "町域", "字丁目", "京都通り名", "事業所名", "事業所住所"]
OUTPUT_COLUMNS = ["郵便番号"] + SEARCH_TARGET_COLUMNS

def tokenize(string):
    """
    文字列を2-gramで分割する
    
    Args:
        string (str): 分割対象の文字列

    Returns:
        list[str]: 2-gramのリスト。
            - 各要素は入力文字列から連続する2文字を抽出したもの
            - 例: "東京都" -> ["東京", "京都"]
    """
    # 引き数の文字列を一文字ずつ分割する
    string_list = list(string)
  
    two_gram_list = []
    for i in range(len(string_list) - 1): 
        # 二文字を一つの要素として格納していく
        two_gram = string_list[i] + string_list[i + 1]
        two_gram_list.append(two_gram)

    return two_gram_list

def extract_address_string(df):
    """
    住所データフレームから、検索対象となる情報を含むカラムの値のみを抽出し、一つの文字列として結合する。
    
    Args:
        df (pandas.DataFrame): 住所情報を含むデータフレーム。

    Returns:
        list[str]: 結合された住所文字列のリスト。
            - 各要素は指定カラムの値を連結した文字列
            - 空白とnanは除去される
    """
    # dfの住所を一行の文字列データとして結合し、配列に追加していく
    address_string_list = []
    for _, row in df.iterrows():
        address_string = ""
        for col in SEARCH_TARGET_COLUMNS:
            value = str(row[col])
            # データが入っている場合のみ文字列に追加
            if value != "nan":
                address_string += value
                
        # スペースを切り詰める
        address_string = ''.join(address_string.split())
        address_string_list.append(address_string)
        
    return address_string_list

def prepare_output_string_list(df, target_index_list):
    """
    データフレームと選択されたインデックスから、指定フォーマットの住所文字列リストを生成する

    Args:
        df (pandas.DataFrame): 住所情報を含むデータフレーム
        target_index_list (list): 抽出対象となるデータフレームの行インデックスのリスト

    Returns:
        list[str]: フォーマット済みの住所文字列のリスト。各要素は以下の形式：
            "郵便番号 都道府県 市区町村町域字丁目京都通り名 事業所名 事業所住所"
    """
    filtered_df = df.loc[target_index_list]
    
    output_list = []

    for _, row in filtered_df.iterrows():
        address_string = ""
        for col in OUTPUT_COLUMNS:
            value = str(row[col])
            if value != "nan":
                address_string += value
            
            if col == "郵便番号":
                address_string += "\u3000"
    
        output_list.append(address_string)
        
    return output_list

def prepare_inverted_index(address_string_list):
    """
    住所文字列のリストから2-gramベースの転置インデックスを作成する
    検索用の住所文字列のリストから2-gramで転置インデックスを生成する

    Args:
        address_string_list (list[str]): 住所文字列のリスト。各要素は結合された住所情報を含む

    Returns:
        defaultdict[str, set[int]]: 転置インデックス。
            - キー: 2文字のトークン（2-gram）
            - 値: そのトークンが出現する住所のインデックスを含む集合
            例：{
                "東京": {1, 2, 3...}, 
                "京都": {2, 3, 4 ...},
                ...
            }
    """
    # キーの存在確認を簡潔にするためにdefaultdictを使用
    # 各トークンに対するインデックス保持はsetで行う
    inverted_index_dict = defaultdict(set)
    
    for index, address_string in enumerate(address_string_list):
        # 文字列を2-gramでトークンに分割
        tokens = tokenize(address_string)
        # トークンをキーとし、その住所データのインデックスをsetに追加
        for token in tokens:
            inverted_index_dict[token].add(index)
            
    return inverted_index_dict

def generate_inverted_index_json(address_string_list):
    inverted_index = prepare_inverted_index(address_string_list)
    
    # jsonファイルにするために、setをリストに変換する
    json_compatible_dict = {}
    for key, value in inverted_index.items():
        json_compatible_dict[key] = list(value)
    
    inverted_index_json = json.dumps(json_compatible_dict, ensure_ascii=False)
    
    return inverted_index_json

def search_address(inverted_index, search_q):
    """
    検索クエリに一致する住所のインデックスを返す。

    Args:
        inverted_index (dict): 転置インデックス
        search_q (string): 検索クエリ文字列

    Returns:
        list[int]: 一致する住所のインデックスリスト
    """
     # search_qをトークンに分割
    search_tokens = tokenize(search_q)
    
    # 最初のトークンで初期化し、以降は積集合を取る
    first_token = search_tokens[0]
    temp_index_set = set(inverted_index[first_token])
    
    # すべてのトークンと照合するindex要素を抽出
    for search_token in search_tokens[1:]:
        target_index_list = inverted_index[search_token]
        temp_index_set &= set(target_index_list)
    
    target_index_list = list(temp_index_set)
    
    return target_index_list

def filter_index(address_string_list, target_index_list, search_q):
    """
    転置インデックスで絞り込んだ結果から、検索クエリを完全一致で含む住所のインデックスのみを抽出する

    Args:
        address_string_list (list[str]): 住所文字列のリスト
        target_index_list (list[int]): 転置インデックスによる検索で絞り込まれた住所のインデックスリスト
        search_q (str): 検索クエリ文字列

    Returns:
        list[int]: 検索クエリを完全一致で含む住所のインデックスリスト
            - 転置インデックスによる検索結果をさらに絞り込んだもの
            - 検索クエリが住所文字列の部分文字列として存在するもののみを含む
    """
    filtered_index_list = []
    
    for target_index in target_index_list:
        if search_q in address_string_list[target_index]:
            filtered_index_list.append(target_index)
    
    return filtered_index_list