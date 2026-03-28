"""
Tests exhaustivos para lead_scoring/utils.py.

Cubre: normalizar_rut, extraer_rut_de_id, tipo_licitacion,
is_persona_natural, formato_clp, safe_get, print_header.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import utils


# ═══════════════════════════════════════════════════════════════════════
# normalizar_rut
# ═══════════════════════════════════════════════════════════════════════

class TestNormalizarRut:
    """Tests para normalizar_rut — normalización de RUT chileno."""

    def test_con_puntos_y_guion(self):
        assert utils.normalizar_rut("76.543.210-K") == "76543210-K"

    def test_sin_puntos_con_guion(self):
        assert utils.normalizar_rut("76543210-K") == "76543210-K"

    def test_sin_guion(self):
        """Sin guión, debe insertarlo antes del dígito verificador."""
        assert utils.normalizar_rut("76543210K") == "76543210-K"

    def test_sin_puntos_sin_guion_digito_numerico(self):
        assert utils.normalizar_rut("765432100") == "76543210-0"

    def test_con_puntos_sin_guion(self):
        assert utils.normalizar_rut("76.543.210K") == "76543210-K"

    def test_k_minuscula(self):
        """k minúscula debe convertirse a K."""
        assert utils.normalizar_rut("76543210-k") == "76543210-K"

    def test_k_minuscula_sin_guion(self):
        assert utils.normalizar_rut("76543210k") == "76543210-K"

    def test_con_espacios(self):
        assert utils.normalizar_rut(" 76543210-K ") == "76543210-K"

    def test_vacio(self):
        assert utils.normalizar_rut("") is None

    def test_none(self):
        assert utils.normalizar_rut(None) is None

    def test_no_string_int(self):
        assert utils.normalizar_rut(12345) is None

    def test_no_string_float(self):
        assert utils.normalizar_rut(76543210.0) is None

    def test_muy_corto_3_chars(self):
        assert utils.normalizar_rut("123") is None

    def test_cinco_digitos_invalido(self):
        """5 dígitos + verificador: inválido (mínimo 6 dígitos)."""
        assert utils.normalizar_rut("12345-6") is None

    def test_minimo_6_digitos(self):
        """6 dígitos es el mínimo válido."""
        assert utils.normalizar_rut("123456-7") == "123456-7"

    def test_maximo_9_digitos(self):
        """9 dígitos es el máximo válido."""
        assert utils.normalizar_rut("123456789-0") == "123456789-0"

    def test_10_digitos_invalido(self):
        assert utils.normalizar_rut("1234567890-1") is None

    def test_solo_letras(self):
        assert utils.normalizar_rut("abcdefgh") is None

    def test_rut_empresa_real(self):
        """RUT formato empresa chilena real."""
        assert utils.normalizar_rut("96.585.660-9") == "96585660-9"

    def test_rut_persona_real(self):
        """RUT formato persona natural."""
        assert utils.normalizar_rut("12.345.678-5") == "12345678-5"


# ═══════════════════════════════════════════════════════════════════════
# extraer_rut_de_id
# ═══════════════════════════════════════════════════════════════════════

class TestExtraerRutDeId:
    """Tests para extraer_rut_de_id — extracción de RUT desde IDs OCDS."""

    def test_formato_ocds_cl_rut(self):
        assert utils.extraer_rut_de_id("CL-RUT-76543210-K") == "76543210-K"

    def test_rut_directo_con_guion(self):
        assert utils.extraer_rut_de_id("76543210-K") == "76543210-K"

    def test_rut_sin_guion_en_id(self):
        """RUT sin guión dentro de un ID."""
        assert utils.extraer_rut_de_id("CL-RUT-76543210K") == "76543210-K"

    def test_texto_random_sin_rut(self):
        assert utils.extraer_rut_de_id("random-text") is None

    def test_vacio(self):
        assert utils.extraer_rut_de_id("") is None

    def test_none(self):
        assert utils.extraer_rut_de_id(None) is None

    def test_no_string(self):
        assert utils.extraer_rut_de_id(12345) is None

    def test_k_minuscula_se_normaliza(self):
        assert utils.extraer_rut_de_id("CL-RUT-76543210-k") == "76543210-K"

    def test_numeros_muy_cortos(self):
        """Números con menos de 6 dígitos no matchean."""
        assert utils.extraer_rut_de_id("12345") is None

    def test_rut_embebido_en_texto_largo(self):
        """RUT embebido dentro de texto más largo."""
        result = utils.extraer_rut_de_id("proveedor-76543210-K-activo")
        assert result == "76543210-K"


# ═══════════════════════════════════════════════════════════════════════
# tipo_licitacion
# ═══════════════════════════════════════════════════════════════════════

class TestTipoLicitacion:
    """Tests para tipo_licitacion — extracción de tipo desde código."""

    def test_lp(self):
        assert utils.tipo_licitacion("XXXX-LP26") == "LP"

    def test_le(self):
        assert utils.tipo_licitacion("XXXX-LE25") == "LE"

    def test_l1(self):
        assert utils.tipo_licitacion("XXXX-L1XX") == "L1"

    def test_lr(self):
        assert utils.tipo_licitacion("XXXX-LR") == "LR"

    def test_lq(self):
        assert utils.tipo_licitacion("XXXX-LQ22") == "LQ"

    def test_otro_sin_tipo(self):
        assert utils.tipo_licitacion("algo-random") == "Otro"

    def test_minusculas(self):
        """Se convierte a upper internamente."""
        assert utils.tipo_licitacion("xxxx-lp26") == "LP"

    def test_mixed_case(self):
        assert utils.tipo_licitacion("Xxxx-Lp26") == "LP"

    def test_con_parentesis(self):
        """Formato alternativo con paréntesis."""
        assert utils.tipo_licitacion("XXXX(LP)26") == "LP"

    def test_none_input(self):
        """None se convierte a str → 'NONE' → no matchea → Otro."""
        assert utils.tipo_licitacion(None) == "Otro"

    def test_numerico(self):
        """Input numérico se convierte a string."""
        assert utils.tipo_licitacion(12345) == "Otro"


# ═══════════════════════════════════════════════════════════════════════
# is_persona_natural
# ═══════════════════════════════════════════════════════════════════════

class TestIsPersonaNatural:
    """Tests para is_persona_natural — detecta personas vs empresas."""

    def test_empresa_constructora(self):
        assert utils.is_persona_natural("CONSTRUCTORA X LTDA") is False

    def test_persona_tres_palabras(self):
        assert utils.is_persona_natural("JUAN PEREZ LOPEZ") is True

    def test_empresa_servicios(self):
        assert utils.is_persona_natural("SERVICIOS Y CIA") is False

    def test_empresa_spa(self):
        assert utils.is_persona_natural("GUERCUT SPA") is False

    def test_empresa_eirl(self):
        assert utils.is_persona_natural("JOSE MARTINEZ E.I.R.L") is False

    def test_empresa_sa(self):
        assert utils.is_persona_natural("GRUPO INDUSTRIAL S.A.") is False

    def test_empresa_inversiones(self):
        assert utils.is_persona_natural("INVERSIONES DEL NORTE LTDA") is False

    def test_con_pipe_empresa(self):
        """Keyword en trade name (parte después del pipe)."""
        assert utils.is_persona_natural("NOMBRE RARO | SERVICIOS GENERALES") is False

    def test_con_pipe_persona(self):
        """Persona natural con pipe — ambas partes sin keywords y cortas."""
        assert utils.is_persona_natural("JUAN PEREZ | Juan Perez") is True

    def test_cinco_palabras_false(self):
        """5 palabras supera el umbral de ≤4 → False."""
        assert utils.is_persona_natural("JUAN PEREZ LOPEZ GARCIA MARTINEZ") is False

    def test_cuatro_palabras_true(self):
        """4 palabras está en el límite ≤4 → True."""
        assert utils.is_persona_natural("JUAN PEREZ LOPEZ GARCIA") is True

    def test_una_palabra(self):
        assert utils.is_persona_natural("JUAN") is True

    def test_vacio(self):
        assert utils.is_persona_natural("") is False

    def test_nan(self):
        assert utils.is_persona_natural(float("nan")) is False

    def test_none(self):
        assert utils.is_persona_natural(None) is False

    def test_con_acentos_empresa(self):
        """Acento en keyword (CONSTRUCCIÓN → CONSTRUCCION) detectado."""
        assert utils.is_persona_natural("CONSTRUCCIÓN OMEGA") is False

    def test_con_acentos_persona(self):
        """Nombre con acentos que no tiene keywords."""
        assert utils.is_persona_natural("JOSÉ MARÍA LÓPEZ") is True

    def test_pipe_muchas_palabras_en_parte(self):
        """5 palabras en una parte del pipe → False."""
        assert utils.is_persona_natural("A B C D E | Corto") is False


# ═══════════════════════════════════════════════════════════════════════
# formato_clp
# ═══════════════════════════════════════════════════════════════════════

class TestFormatoClp:
    """Tests para formato_clp — formateo de pesos chilenos."""

    def test_billones(self):
        assert utils.formato_clp(1_500_000_000) == "$1.5B"

    def test_exacto_un_billon(self):
        assert utils.formato_clp(1_000_000_000) == "$1.0B"

    def test_2_5_billones(self):
        assert utils.formato_clp(2_500_000_000) == "$2.5B"

    def test_millones(self):
        assert utils.formato_clp(50_000_000) == "$50M"

    def test_exacto_un_millon(self):
        assert utils.formato_clp(1_000_000) == "$1M"

    def test_monto_tipico_150m(self):
        assert utils.formato_clp(150_000_000) == "$150M"

    def test_miles(self):
        assert utils.formato_clp(500_000) == "$500,000"

    def test_menos_de_un_millon(self):
        assert utils.formato_clp(999_999) == "$999,999"

    def test_cero(self):
        assert utils.formato_clp(0) == "$0"

    def test_nan(self):
        assert utils.formato_clp(float("nan")) == "$0"

    def test_none(self):
        assert utils.formato_clp(None) == "$0"

    def test_np_nan(self):
        assert utils.formato_clp(np.nan) == "$0"

    def test_negativo_no_crashea(self):
        """Valor negativo se formatea sin crash."""
        result = utils.formato_clp(-500_000)
        assert "$" in result


# ═══════════════════════════════════════════════════════════════════════
# safe_get
# ═══════════════════════════════════════════════════════════════════════

class TestSafeGet:
    """Tests para safe_get — acceso seguro a Series con manejo de NaN."""

    def test_valor_numerico(self):
        row = pd.Series({"col": 42})
        assert utils.safe_get(row, "col") == 42

    def test_valor_string(self):
        row = pd.Series({"col": "hello"})
        assert utils.safe_get(row, "col") == "hello"

    def test_nan_retorna_none(self):
        row = pd.Series({"col": float("nan")})
        assert utils.safe_get(row, "col") is None

    def test_nan_con_default(self):
        row = pd.Series({"col": float("nan")})
        assert utils.safe_get(row, "col", default=0) == 0

    def test_np_nan(self):
        row = pd.Series({"col": np.nan})
        assert utils.safe_get(row, "col") is None

    def test_none_valor(self):
        row = pd.Series({"col": None})
        assert utils.safe_get(row, "col") is None

    def test_columna_no_existe(self):
        row = pd.Series({"a": 10})
        assert utils.safe_get(row, "b") is None

    def test_columna_no_existe_con_default(self):
        row = pd.Series({"a": 10})
        assert utils.safe_get(row, "b", default="N/A") == "N/A"

    def test_cero_no_es_none(self):
        """0 es un valor válido, no debe tratarse como NaN."""
        row = pd.Series({"col": 0})
        assert utils.safe_get(row, "col") == 0

    def test_false_no_es_none(self):
        """False es un valor válido, no debe tratarse como NaN.
        Usa == en vez de 'is' porque pandas retorna numpy.bool_."""
        row = pd.Series({"col": False})
        assert utils.safe_get(row, "col") == False  # noqa: E712

    def test_string_vacio_es_valido(self):
        """String vacío es un valor válido."""
        row = pd.Series({"col": ""})
        assert utils.safe_get(row, "col") == ""

    def test_lista_es_valida(self):
        """Lista se retorna sin pasarla por pd.isna."""
        row = pd.Series({"col": [1, 2, 3]})
        assert utils.safe_get(row, "col") == [1, 2, 3]


# ═══════════════════════════════════════════════════════════════════════
# print_header
# ═══════════════════════════════════════════════════════════════════════

class TestPrintHeader:
    """Tests para print_header — no debe crashear."""

    def test_output_contiene_texto(self, capsys):
        utils.print_header("Test Header")
        captured = capsys.readouterr()
        assert "Test Header" in captured.out

    def test_tiene_separadores(self, capsys):
        utils.print_header("Algo")
        captured = capsys.readouterr()
        assert "=" * 60 in captured.out

    def test_vacio_no_crashea(self, capsys):
        utils.print_header("")
        captured = capsys.readouterr()
        assert "=" in captured.out
