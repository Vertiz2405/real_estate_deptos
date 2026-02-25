import streamlit as st
import pandas as pd
import re

from excel_io import read_deptos_excel, write_deptos_excel, compute_fields, DECISION_OPTIONS, now_str
import hashlib
import io


st.set_page_config(page_title="Revisión Deptos (Cliente)", layout="wide")
st.markdown("""
<style>
.block-container { padding-top: 2.2rem; padding-bottom: 2.2rem; max-width: 1200px; }
h1 { letter-spacing: -0.02em; }
.small-muted { color: rgba(255,255,255,0.65); font-size: 0.95rem; }

/* Cards */
.card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 18px;
  padding: 16px 18px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}
.card-title { font-weight: 700; font-size: 0.95rem; opacity: 0.85; margin-bottom: 6px; }
.card-value { font-weight: 800; font-size: 1.6rem; letter-spacing: -0.02em; }

/* Chips */
.chips { margin-top: 6px; }
.chip {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.06);
  margin-right: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}
.chip-ok { border-color: rgba(16,185,129,0.4); background: rgba(16,185,129,0.12); }
.chip-bad { border-color: rgba(239,68,68,0.4); background: rgba(239,68,68,0.12); }
.chip-warn { border-color: rgba(59,130,246,0.4); background: rgba(59,130,246,0.12); }
.chip-muted { opacity: 0.55; }

/* Photo frame */
.photo {
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.10);
  overflow: hidden;
}
</style>
""", unsafe_allow_html=True)



def is_http_url(s: str) -> bool:
    if not isinstance(s, str):
        return False
    s = s.strip()
    return s.startswith("http://") or s.startswith("https://")


def parse_fotos(cell):
    if not isinstance(cell, str) or not cell.strip():
        return []
    # SOLO separa por ; o salto de línea
    parts = re.split(r"[;\n]+", cell)
    return [p.strip() for p in parts if p.strip()]


def df_signature(df_: pd.DataFrame) -> str:
    b = pd.util.hash_pandas_object(df_, index=True).values.tobytes()
    return hashlib.md5(b).hexdigest()


def safe_image(url: str, caption: str | None = None):
    """
    Muestra imagen sin tirar la app si el link falla.
    """
    try:
        st.image(url, use_column_width=True, caption=caption)
    except Exception:
        st.warning("⚠️ No pude cargar una imagen (link inválido o bloqueado).")
        if is_http_url(url):
            st.caption(url)


st.markdown("## Revisión de departamentos")
st.markdown(
    '<div class="small-muted">Sube el Excel → revisa por pestañas → marca Apoya/Descarta/Visitar → descarga Excel actualizado.</div>',
    unsafe_allow_html=True
)

uploaded = st.file_uploader("Sube el Excel (deptos.xlsx)", type=["xlsx"])
if not uploaded:
    st.info("Sube un Excel para empezar.")
    st.stop()

file_bytes = uploaded.getvalue()
file_sig = hashlib.md5(file_bytes).hexdigest()

try:
    df = read_deptos_excel(uploaded)
except Exception as e:
    st.error(f"No pude leer el Excel: {e}")
    st.stop()

# Summary
df = compute_fields(df)
counts = df["decision_status"].value_counts(dropna=False).to_dict()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="card"><div class="card-title">Apoya</div><div class="card-value">{int(counts.get("Apoya", 0))}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="card"><div class="card-title">Descarta</div><div class="card-value">{int(counts.get("Descarta", 0))}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="card"><div class="card-title">Visitar</div><div class="card-value">{int(counts.get("Visitar", 0))}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="card"><div class="card-title">Pendiente</div><div class="card-value">{int(counts.get("Pendiente", 0))}</div></div>', unsafe_allow_html=True)

st.divider()

# Tabs by nombre, but internally update by id
names = [f"{int(df.loc[i,'id'])} · {str(df.loc[i,'nombre'] or 'Sin nombre')}" for i in range(len(df))]
tabs = st.tabs(names)

# Keep a mutable copy in session
if "df_client" not in st.session_state or st.session_state.get("df_client_source") != file_sig:
    st.session_state.df_client = df.copy()
    st.session_state.df_client_source = file_sig

df_mut = st.session_state.df_client

for i, tab in enumerate(tabs):
    with tab:
        row_id = int(df_mut.loc[i, "id"])
        nombre = str(df_mut.loc[i, "nombre"] or f"Depto {row_id}")

        left, right = st.columns([1.1, 1])

        with left:
            st.subheader(nombre)
            status = str(df_mut.loc[i, "decision_status"] or "Pendiente")
            color = {"Apoya": "chip-ok", "Descarta": "chip-bad", "Visitar": "chip-warn", "Pendiente": "chip-muted"}.get(status, "chip-muted")
            st.markdown(f'<div class="chips"><span class="chip {color}">Estatus: {status}</span></div>', unsafe_allow_html=True)
            st.write(df_mut.loc[i, "zona_colonia"] or "")

            fotos = parse_fotos(df_mut.loc[i, "fotos_urls"])

            if fotos:
                st.markdown("### Fotos")
                main, side = st.columns([1.6, 1])

                with main:
                    st.markdown('<div class="photo">', unsafe_allow_html=True)
                    safe_image(fotos[0])
                    st.markdown('</div>', unsafe_allow_html=True)

                with side:
                    thumbs = fotos[1:5]
                    if thumbs:
                        for url_img in thumbs:
                            st.markdown('<div class="photo">', unsafe_allow_html=True)
                            safe_image(url_img)
                            st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Sin fotos (o links no válidos).")

            p1, p2, p3, p4 = st.columns([1.6, 1, 1.5, 1])
            p1.metric("Precio", f"${int(df_mut.loc[i, 'precio_mxn']):,}" if pd.notna(df_mut.loc[i, "precio_mxn"]) else "-")
            p2.metric("m²", f"{df_mut.loc[i, 'm2_construccion']:.0f}" if pd.notna(df_mut.loc[i, "m2_construccion"]) else "-")
            p3.metric("$/m²", f"${df_mut.loc[i, 'precio_por_m2']:.0f}" if pd.notna(df_mut.loc[i, "precio_por_m2"]) else "-")
            p4.metric("Tipo", str(df_mut.loc[i, "tipo"] or "-"))

            a1, a2, a3 = st.columns(3)
            a1.metric("Recámaras", int(df_mut.loc[i, "recamaras"]) if pd.notna(df_mut.loc[i, "recamaras"]) else 0)
            a2.metric("Baños", int(df_mut.loc[i, "banos"]) if pd.notna(df_mut.loc[i, "banos"]) else 0)
            a3.metric("Estac.", int(df_mut.loc[i, "estacionamientos"]) if pd.notna(df_mut.loc[i, "estacionamientos"]) else 0)

            url = df_mut.loc[i, "url"]
            if isinstance(url, str) and url.strip():
                st.link_button("Abrir publicación", url.strip())

            st.caption("Flags")
            chips = []
            if df_mut.loc[i, "flag_tren_ruido"]:
                chips.append(("🚆 Tren/ruido", "chip-bad"))
            if df_mut.loc[i, "flag_loft_sin_rec"]:
                chips.append(("🏙️ Loft sin rec", "chip-warn"))
            if df_mut.loc[i, "flag_fuera_presupuesto"]:
                chips.append(("💸 Fuera presupuesto", "chip-bad"))
            if df_mut.loc[i, "flag_pocos_deptos"]:
                chips.append(("🏢 Pocos deptos", "chip-ok"))

            if not chips:
                st.markdown('<div class="chips"><span class="chip chip-muted">Sin flags</span></div>', unsafe_allow_html=True)
            else:
                html = '<div class="chips">' + "".join([f'<span class="chip {cls}">{txt}</span>' for txt, cls in chips]) + '</div>'
                st.markdown(html, unsafe_allow_html=True)

        with right:
            st.markdown("### Pros")
            st.markdown(f'<div class="card">{(df_mut.loc[i, "pros"] or "—")}</div>', unsafe_allow_html=True)

            st.markdown("### Contras")
            st.markdown(f'<div class="card">{(df_mut.loc[i, "contras"] or "—")}</div>', unsafe_allow_html=True)

            st.markdown("### Notas")
            st.markdown(f'<div class="card">{(df_mut.loc[i, "notas"] or "—")}</div>', unsafe_allow_html=True)

        st.divider()
        st.markdown("### Decisión")

        d1, d2, d3 = st.columns([1, 2, 1])

        with d1:
            current = str(df_mut.loc[i, "decision_status"] or "Pendiente")
            if current not in DECISION_OPTIONS:
                current = "Pendiente"
            new_status = st.selectbox(
                "Estatus",
                DECISION_OPTIONS,
                index=DECISION_OPTIONS.index(current),
                key=f"status_{row_id}",
            )

        with d2:
            comment = st.text_input(
                "Comentario",
                value=str(df_mut.loc[i, "decision_comentario"] or ""),
                key=f"comment_{row_id}",
            )

        with d3:
            who = st.text_input(
                "Quién decide (opcional)",
                value=str(df_mut.loc[i, "decision_quien"] or ""),
                key=f"who_{row_id}",
            )

        idx = df_mut.index[df_mut["id"] == row_id]
        if len(idx) == 1:
            j = idx[0]
            df_mut.loc[j, "decision_status"] = new_status
            df_mut.loc[j, "decision_comentario"] = comment.strip() if comment else None
            df_mut.loc[j, "decision_quien"] = who.strip() if who else None
            df_mut.loc[j, "decision_fecha"] = now_str()

st.session_state.df_client = compute_fields(df_mut)

st.divider()
st.subheader("Descargar Excel actualizado")
out_name = st.text_input("Nombre de salida", value="deptos_actualizado.xlsx")


@st.cache_data(show_spinner=False)
def build_excel_bytes(df_, sig: str):
    b = io.BytesIO()
    write_deptos_excel(df_, b)
    b.seek(0)
    return b.getvalue()


sig = df_signature(st.session_state.df_client)
data = build_excel_bytes(st.session_state.df_client, sig)
st.download_button(
    "Descargar Excel actualizado",
    data=data,
    file_name=out_name,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)