"""
Pandas Dataframe related utils
"""

import pandas as pd


##############################################################################
#                                DF MANIPULATION                             #
##############################################################################


def df_to_json_safe(df: pd.DataFrame, index_as: str = "rows") -> dict:
    """
    Convierte un DataFrame en un dict JSON-safe, transformando columnas
    Timestamp a str.

    Args:
        df (pd.DataFrame): DataFrame a convertir.
        index_as (str): 'rows' para dict por filas, 'columns' para dict por
                        columnas (default: 'rows').
                        Internamente usa orient='index' o 'columns'.

    Returns:
        dict: Diccionario serializable a JSON.
    """
    if df.empty:
        return {}

    df = df.copy()

    # Asegurar que las columnas (que suelen ser Timestamp) se convierten a str
    df.columns = [
        str(col.date()) if isinstance(col, pd.Timestamp) else str(col)
        for col in df.columns
    ]

    # También podemos asegurar que el índice es string
    df.index = [str(idx) for idx in df.index]

    if index_as == "rows":
        return df.to_dict(orient="index")
    else:
        raise ValueError("index_as debe ser 'rows'")


def series_to_json_safe(series: pd.Series) -> dict:
    """
    Convierte una Series en un dict JSON-safe, transformando índices
    Timestamp a str.

    Args:
        series (pd.Series): Series a convertir.

    Returns:
        dict: Diccionario serializable a JSON.
    """
    if series.empty:
        return {}

    series = series.copy()

    # Asegurar que los índices (que suelen ser Timestamp) se convierten a str
    series.index = [
        str(idx.date()) if isinstance(idx, pd.Timestamp) else str(idx)
        for idx in series.index
    ]

    return series.to_dict()
