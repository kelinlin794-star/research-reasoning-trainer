# -*- coding: utf-8 -*-
"""
文献检索模块 —— 封装 OpenAlex 免费学术 API。

能力：
1. search_papers    —— 按关键词搜索论文
2. get_work         —— 获取单篇论文详情（含引用关系）
3. get_references   —— 前置论文（这篇引用了谁）
4. get_citations    —— 后续论文（谁引用了这篇）
5. get_related      —— 相关论文

OpenAlex 免费、无需 API key，是全字段开放的学术图谱，适合做「演进链」。
"""

import requests

OPENALEX_SEARCH = "https://api.openalex.org/works"
OPENALEX_WORK = "https://api.openalex.org/works/{work_id}"

# 只取需要的字段，减小响应体积
SELECT_FIELDS = (
    "id,title,display_name,publication_year,cited_by_count,"
    "authorships,doi,primary_location,referenced_works,related_works"
)


def _normalize(work: dict) -> dict:
    """把 OpenAlex 返回的作品对象整理成简洁结构。"""
    authors = []
    for a in work.get("authorships", [])[:5]:
        authors.append(a.get("author", {}).get("display_name", ""))
    return {
        "id": work.get("id", "").split("/")[-1],
        "title": work.get("display_name") or work.get("title") or "",
        "year": work.get("publication_year"),
        "cited_by_count": work.get("cited_by_count", 0),
        "authors": [x for x in authors if x],
        "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
        "referenced_works": work.get("referenced_works", []),
        "related_works": work.get("related_works", []),
    }


def search_papers(query: str, limit: int = 5) -> list:
    """按关键词搜索论文，按被引次数降序返回。"""
    resp = requests.get(
        OPENALEX_SEARCH,
        params={
            "search": query,
            "per-page": limit,
            "select": SELECT_FIELDS,
            "sort": "cited_by_count:desc",
        },
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [_normalize(w) for w in results]


def search_by_title(title: str, limit: int = 3) -> list:
    """按标题精确搜索（用 title.search 过滤，避免被高被引但无关的论文干扰）。"""
    resp = requests.get(
        OPENALEX_SEARCH,
        params={
            "filter": f"title.search:{title}",
            "per-page": limit,
            "select": SELECT_FIELDS,
            "sort": "cited_by_count:desc",
        },
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [_normalize(w) for w in results]


def get_work(work_id: str) -> dict:
    """获取单篇论文详情（含引用关系字段）。"""
    url = OPENALEX_WORK.format(work_id=work_id)
    resp = requests.get(url, params={"select": SELECT_FIELDS}, timeout=20)
    resp.raise_for_status()
    return _normalize(resp.json())


def _fetch_works(urls: list, limit: int) -> list:
    """批量获取一批 work 的详情（按 id 过滤查询）。"""
    if not urls:
        return []
    ids = [u.split("/")[-1] for u in urls[:50]]
    resp = requests.get(
        OPENALEX_SEARCH,
        params={
            "filter": "openalex_id:" + "|".join(ids),
            "per-page": min(limit, len(ids)),
            "select": SELECT_FIELDS,
        },
        timeout=25,
    )
    resp.raise_for_status()
    return [_normalize(w) for w in resp.json().get("results", [])]


def get_references(work_id: str, limit: int = 8) -> list:
    """前置论文：这篇引用了谁。"""
    work = get_work(work_id)
    return _fetch_works(work.get("referenced_works", []), limit)


def get_citations(work_id: str, limit: int = 8) -> list:
    """后续论文：谁引用了这篇。"""
    resp = requests.get(
        OPENALEX_SEARCH,
        params={
            "filter": f"cites:{work_id}",
            "per-page": limit,
            "select": SELECT_FIELDS,
            "sort": "cited_by_count:desc",
        },
        timeout=25,
    )
    resp.raise_for_status()
    return [_normalize(w) for w in resp.json().get("results", [])]


def get_related(work_id: str, limit: int = 8) -> list:
    """相关论文。"""
    work = get_work(work_id)
    return _fetch_works(work.get("related_works", []), limit)
