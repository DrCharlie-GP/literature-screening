# -*- coding: utf-8 -*-
"""
数据加载与解析模块
负责读取和解析各种格式的文献文件
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd


# 常量定义
SUPPORTED_EXTENSIONS = {
    ".csv", ".xlsx", ".xls", ".tsv",
    ".json", ".jsonl", ".ris", ".nbib", ".txt",
}

STANDARD_COLUMNS = [
    "title", "author", "abstract", "keywords",
    "doi", "publication_year", "journal",
    "source_file", "source_format",
]

COLUMN_ALIASES = {
    "title": "title", "article title": "title",
    "document title": "title", "ti": "title", "t1": "title",
    "author": "author", "authors": "author",
    "au": "author", "a1": "author", "af": "author",
    "abstract": "abstract", "ab": "abstract", "summary": "abstract",
    "keywords": "keywords", "keyword": "keywords",
    "author keywords": "keywords", "keywords plus": "keywords",
    "kw": "keywords", "ak": "keywords", "de": "keywords",
    "doi": "doi", "di": "doi", "do": "doi",
    "publication year": "publication_year", "year": "publication_year",
    "py": "publication_year", "y1": "publication_year",
    "journal": "journal", "source": "journal",
    "so": "journal", "jo": "journal", "jf": "journal",
    "jt": "journal", "ta": "journal", "t2": "journal",
}


class DataLoaderError(Exception):
    """数据加载异常"""
    pass


def safe_str(x: Any) -> str:
    """安全转换为字符串"""
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x).strip()


def normalize_colname(col: str) -> str:
    """标准化列名"""
    col = safe_str(col).lower()
    col = re.sub(r"[\n\r\t]+", " ", col)
    col = re.sub(r"\s+", " ", col)
    return col.strip()


def normalize_text_for_dedup(text: str) -> str:
    """标准化文本用于去重"""
    text = safe_str(text).lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def normalize_doi(doi: str) -> str:
    """标准化DOI"""
    doi = safe_str(doi).lower()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    doi = doi.replace("doi:", "").strip()
    return doi


def extract_year(text: str) -> str:
    """提取年份"""
    text = safe_str(text)
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return m.group(0) if m else text.strip()


def ensure_standard_columns(df: pd.DataFrame) -> pd.DataFrame:
    """确保存在标准列"""
    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df


def standardize_columns(df: pd.DataFrame, extra_aliases: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """标准化列名"""
    alias_map = dict(COLUMN_ALIASES)
    if extra_aliases:
        alias_map.update(extra_aliases)
    rename_map = {}
    for col in df.columns:
        norm = normalize_colname(col)
        rename_map[col] = alias_map.get(norm, col)
    df = df.rename(columns=rename_map)
    return ensure_standard_columns(df)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """清洗数据框"""
    df = df.copy()
    df = ensure_standard_columns(df)
    for col in STANDARD_COLUMNS:
        df[col] = df[col].apply(safe_str)
    for col in ["title", "author", "abstract", "keywords", "journal"]:
        df[col] = df[col].str.replace(r"\s+", " ", regex=True).str.strip()
    df["doi"] = df["doi"].apply(normalize_doi)
    df["publication_year"] = df["publication_year"].apply(extract_year)
    return df


def deduplicate_records(df: pd.DataFrame) -> pd.DataFrame:
    """去重记录"""
    df = df.copy()
    df["doi_key"] = df["doi"].apply(normalize_doi)
    df["title_key"] = df["title"].apply(normalize_text_for_dedup)
    
    has_doi = df["doi_key"] != ""
    no_doi = ~has_doi
    
    df1 = df[has_doi].drop_duplicates(subset=["doi_key"], keep="first")
    df2 = df[no_doi].drop_duplicates(subset=["title_key"], keep="first")
    
    out = pd.concat([df1, df2], ignore_index=True)
    return out.drop(columns=["doi_key", "title_key"], errors="ignore")


def read_table_like_file(file_path: str) -> pd.DataFrame:
    """读取表格类文件"""
    ext = Path(file_path).suffix.lower()
    if ext == ".csv":
        return pd.read_csv(file_path, dtype=str)
    if ext == ".tsv":
        return pd.read_csv(file_path, sep="\t", dtype=str)
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(file_path, dtype=str)
    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = pd.read_json(f)
        return pd.DataFrame(data)
    if ext == ".jsonl":
        rows = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(pd.read_json(line, typ='series').to_dict())
        return pd.DataFrame(rows)
    raise DataLoaderError(f"不支持的表格格式: {file_path}")


def read_text_head(file_path: str, n_chars: int = 8000) -> str:
    """读取文件头部内容"""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(n_chars)


def detect_tagged_text_format(file_path: str) -> str:
    """检测标记文本格式"""
    ext = Path(file_path).suffix.lower()
    if ext == ".nbib":
        return "nbib"
    if ext == ".ris":
        return "ris"
    
    content = read_text_head(file_path).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip("\n") for line in content.split("\n") if line.strip()]
    if not lines:
        return "unknown_txt"
    
    joined = "\n".join(lines[:100])
    
    # 检测PubMed格式
    pubmed_score = 0
    if re.search(r"^PMID- ", joined, re.M):
        pubmed_score += 3
    if re.search(r"^TI  - ", joined, re.M):
        pubmed_score += 2
    if re.search(r"^AB  - ", joined, re.M):
        pubmed_score += 2
    if re.search(r"^FAU - ", joined, re.M):
        pubmed_score += 2
    if re.search(r"^DP  - ", joined, re.M):
        pubmed_score += 2
    if re.search(r"^JT  - ", joined, re.M):
        pubmed_score += 1
    if re.search(r"^MH  - ", joined, re.M):
        pubmed_score += 1
    
    # 检测WoS格式
    wos_score = 0
    if re.search(r"^PT ", joined, re.M):
        wos_score += 3
    if re.search(r"^AU ", joined, re.M):
        wos_score += 2
    if re.search(r"^AF ", joined, re.M):
        wos_score += 2
    if re.search(r"^TI ", joined, re.M):
        wos_score += 2
    if re.search(r"^SO ", joined, re.M):
        wos_score += 2
    if re.search(r"^DE ", joined, re.M):
        wos_score += 1
    if re.search(r"^AB ", joined, re.M):
        wos_score += 2
    if re.search(r"^DI ", joined, re.M):
        wos_score += 2
    if re.search(r"^ER\s*$", joined, re.M):
        wos_score += 3
    
    # 检测RIS格式
    ris_score = 0
    if re.search(r"^TY  - ", joined, re.M):
        ris_score += 3
    if re.search(r"^AU  - ", joined, re.M):
        ris_score += 1
    if re.search(r"^TI  - ", joined, re.M):
        ris_score += 1
    if re.search(r"^ER  -", joined, re.M):
        ris_score += 3
    
    if ris_score >= max(pubmed_score, wos_score) and ris_score >= 3:
        return "ris"
    if pubmed_score >= wos_score and pubmed_score >= 3:
        return "pubmed_tagged_txt"
    if wos_score > pubmed_score and wos_score >= 3:
        return "wos_tagged_txt"
    
    return "unknown_txt"


def parse_ris(file_path: str) -> pd.DataFrame:
    """解析RIS格式"""
    records = []
    current = {}
    
    def append_multi_value(field: str, value: str):
        if current.get(field):
            current[field] += "; " + value
        else:
            current[field] = value
    
    def flush():
        nonlocal current
        if current:
            records.append(current)
            current = {}
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue
            m = re.match(r"^([A-Z0-9]{2})  -\s?(.*)$", line)
            if not m:
                continue
            tag, value = m.group(1), m.group(2).strip()
            
            if tag == "ER":
                flush()
                continue
            elif tag in ("TI", "T1", "CT"):
                current["title"] = (current.get("title", "") + " " + value).strip()
            elif tag in ("AU", "A1", "A2", "A3", "A4"):
                append_multi_value("author", value)
            elif tag == "AB":
                current["abstract"] = (current.get("abstract", "") + " " + value).strip()
            elif tag == "KW":
                append_multi_value("keywords", value)
            elif tag in ("DO", "DI"):
                current["doi"] = value
            elif tag in ("PY", "Y1"):
                current["publication_year"] = extract_year(value)
            elif tag in ("JO", "JF", "JA", "T2"):
                current["journal"] = value
    
    flush()
    return pd.DataFrame(records)


def parse_pubmed_nbib_or_tagged(file_path: str) -> pd.DataFrame:
    """解析PubMed NBIB或标记文本格式"""
    records = []
    current = {}
    current_field = None
    
    def append_multi_value(field: str, value: str):
        if current.get(field):
            current[field] += "; " + value
        else:
            current[field] = value
    
    def flush():
        nonlocal current, current_field
        if current:
            records.append(current)
        current = {}
        current_field = None
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            
            if re.match(r"^PMID- ", line):
                if current:
                    flush()
                current["pmid"] = line.split("PMID-", 1)[1].strip()
                current_field = None
                continue
            
            m = re.match(r"^([A-Z]{2,4})\s*-\s?(.*)$", line)
            if m:
                tag = m.group(1).strip()
                value = m.group(2).strip()
                current_field = tag
                
                if tag == "TI":
                    current["title"] = (current.get("title", "") + " " + value).strip()
                elif tag == "AB":
                    current["abstract"] = (current.get("abstract", "") + " " + value).strip()
                elif tag in ("FAU", "AU"):
                    append_multi_value("author", value)
                elif tag in ("OT", "MH"):
                    append_multi_value("keywords", value)
                elif tag in ("JT", "TA"):
                    current["journal"] = (current.get("journal", "") + " " + value).strip()
                elif tag == "DP":
                    current["publication_year"] = extract_year(value)
                elif tag in ("AID", "LID"):
                    doi_match = re.search(r"(10\.\S+?)(?:\s*\[doi\])?$", value, re.I)
                    if doi_match and not current.get("doi"):
                        current["doi"] = doi_match.group(1).strip()
                continue
            
            if re.match(r"^\s{2,}", raw_line) and current_field:
                continuation = line.strip()
                if current_field == "TI":
                    current["title"] = (current.get("title", "") + " " + continuation).strip()
                elif current_field == "AB":
                    current["abstract"] = (current.get("abstract", "") + " " + continuation).strip()
                elif current_field in ("JT", "TA"):
                    current["journal"] = (current.get("journal", "") + " " + continuation).strip()
                elif current_field in ("OT", "MH"):
                    append_multi_value("keywords", continuation)
                continue
    
    if current:
        flush()
    return pd.DataFrame(records)


def parse_wos_tagged_txt(file_path: str) -> pd.DataFrame:
    """解析WoS标记文本格式"""
    records = []
    current = {}
    current_field = None
    
    def append_multi_value(field: str, value: str):
        if current.get(field):
            current[field] += "; " + value
        else:
            current[field] = value
    
    def flush():
        nonlocal current, current_field
        if current:
            records.append(current)
        current = {}
        current_field = None
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            
            if re.match(r"^ER\s*$", line):
                flush()
                continue
            
            m = re.match(r"^([A-Z0-9]{2})\s(.*)$", line)
            if m:
                tag = m.group(1).strip()
                value = m.group(2).strip()
                current_field = tag
                
                if tag == "TI":
                    current["title"] = (current.get("title", "") + " " + value).strip()
                elif tag in ("AU", "AF"):
                    append_multi_value("author", value)
                elif tag == "AB":
                    current["abstract"] = (current.get("abstract", "") + " " + value).strip()
                elif tag in ("DE", "AK", "ID"):
                    append_multi_value("keywords", value)
                elif tag == "DI":
                    current["doi"] = value
                elif tag == "PY":
                    current["publication_year"] = extract_year(value)
                elif tag == "SO":
                    current["journal"] = (current.get("journal", "") + " " + value).strip()
                continue
            
            if re.match(r"^\s{3,}", raw_line) and current_field:
                continuation = line.strip()
                if current_field == "TI":
                    current["title"] = (current.get("title", "") + " " + continuation).strip()
                elif current_field == "AB":
                    current["abstract"] = (current.get("abstract", "") + " " + continuation).strip()
                elif current_field == "SO":
                    current["journal"] = (current.get("journal", "") + " " + continuation).strip()
                elif current_field in ("DE", "AK", "ID"):
                    append_multi_value("keywords", continuation)
                elif current_field in ("AU", "AF"):
                    append_multi_value("author", continuation)
                continue
    
    if current:
        flush()
    return pd.DataFrame(records)


def read_single_file_with_log(file_path: str, extra_aliases: Optional[Dict[str, str]] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """读取单个文件并返回日志"""
    ext = Path(file_path).suffix.lower()
    log_item = {
        "source_file": os.path.basename(file_path),
        "full_path": file_path,
        "detected_format": "",
        "status": "success",
        "record_count": 0,
        "note": "",
    }
    
    try:
        if ext in {".csv", ".xlsx", ".xls", ".tsv", ".json", ".jsonl"}:
            df = read_table_like_file(file_path)
            detected = f"table_like_{ext.lstrip('.')}"
        elif ext == ".ris":
            df = parse_ris(file_path)
            detected = "ris"
        elif ext == ".nbib":
            df = parse_pubmed_nbib_or_tagged(file_path)
            detected = "nbib"
        elif ext == ".txt":
            detected_txt = detect_tagged_text_format(file_path)
            if detected_txt == "pubmed_tagged_txt":
                df = parse_pubmed_nbib_or_tagged(file_path)
            elif detected_txt == "wos_tagged_txt":
                df = parse_wos_tagged_txt(file_path)
            elif detected_txt == "ris":
                df = parse_ris(file_path)
            else:
                raise DataLoaderError("无法自动识别该 txt 文件的文献导出格式")
            detected = detected_txt
        else:
            raise DataLoaderError(f"不支持的文件类型: {ext}")
        
        df = standardize_columns(df, extra_aliases=extra_aliases)
        df["source_file"] = os.path.basename(file_path)
        df["source_format"] = detected
        df = clean_dataframe(df)
        
        log_item["detected_format"] = detected
        log_item["record_count"] = len(df)
        return df, log_item
    
    except Exception as e:
        log_item["status"] = "failed"
        log_item["note"] = str(e)
        return pd.DataFrame(columns=STANDARD_COLUMNS), log_item


def load_all_files_from_folder(input_folder: str, extra_aliases: Optional[Dict[str, str]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """加载文件夹中所有支持的文件"""
    if not os.path.isdir(input_folder):
        raise DataLoaderError(f"输入文件夹不存在: {input_folder}")
    
    files = []
    for root, _, filenames in os.walk(input_folder):
        for name in filenames:
            ext = Path(name).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(os.path.join(root, name))
    
    files = sorted(files)
    if not files:
        raise DataLoaderError("输入文件夹中没有发现支持的文件")
    
    all_dfs = []
    logs = []
    
    for fp in files:
        print(f"[INFO] 正在读取: {fp}")
        df, log_item = read_single_file_with_log(fp, extra_aliases=extra_aliases)
        logs.append(log_item)
        if not df.empty:
            all_dfs.append(df)
    
    log_df = pd.DataFrame(logs)
    
    if not all_dfs:
        raise DataLoaderError("所有文件都未成功解析，请查看 parse_log")
    
    merged = pd.concat(all_dfs, ignore_index=True)
    return merged, log_df


def load_records(input_path: str, extra_aliases: Optional[Dict[str, str]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """加载文献记录，支持文件或文件夹"""
    input_path = os.path.abspath(os.path.expanduser((input_path or "").strip()))
    if not input_path:
        raise DataLoaderError("input_path 不能为空。")
    
    if os.path.isdir(input_path):
        return load_all_files_from_folder(input_path, extra_aliases=extra_aliases)
    
    df, log_item = read_single_file_with_log(input_path, extra_aliases=extra_aliases)
    if df.empty:
        raise DataLoaderError(f"无法从输入文件读取有效文献记录: {input_path}")
    
    return df, pd.DataFrame([log_item])
