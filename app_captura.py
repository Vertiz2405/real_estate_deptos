import streamlit as st
import pandas as pd

from excel_io import DEFAULT_COLUMNS, ensure_schema, compute_fields, write_deptos_excel, read_deptos_excel, now_str

st.set_page_config(page_title="Captura Deptos (Interno)", layout="wide")

st.title("Captura rápida de departamentos (Interno)")
st.caption("Capturas tú todo → exportas Excel bonito.")

if "df" not in st.session_state:
    st.session_state.df = ensure_schema(pd.DataFrame(columns=DEFAULT_COLUMNS))

df = st.session_state.df.copy()

with st.sidebar:
    st.subheader("Acciones")
    uploaded = st.file_uploader("Importar Excel existente (opcional)", type=["xlsx"])
    if uploaded is not None and st.session_state.get("last_uploaded_name") != uploaded.name:
        try:
            st.session_state.df = read_deptos_excel(uploaded)
            st.session_state.last_uploaded_name = uploaded.name
            st.session_state.pop("editor", None)
            st.success("Excel importado.")
            st.rerun()
        except Exception as e:
            st.error(f"No pude leer el Excel: {e}")

    st.divider()
    st.subheader("Nuevo depto (rápido)")
    with st.form("new_depto", clear_on_submit=True):
        nombre = st.text_input("Nombre* (ej. 'Depto 2 - Juan Manuel Vallarta')")
        zona = st.text_input("Zona/Colonia")
        fuente = st.selectbox("Fuente", ["CasasyTerrenos", "EasyBroker", "Inmuebles24", "Otro"], index=0)
        url = st.text_input("URL")
        precio = st.number_input("Precio (MXN)", min_value=0, step=50000, value=0)
        m2 = st.number_input("m² construcción*", min_value=0.0, step=1.0, value=0.0)
        rec = st.number_input("Recámaras", min_value=0, step=1, value=0)
        ban = st.number_input("Baños", min_value=0, step=1, value=0)
        est = st.number_input("Estacionamientos", min_value=0, step=1, value=0)
        tipo = st.text_input("Tipo (Loft / 1 rec / 2 rec...)")
        nuevo = st.selectbox("Nuevo", ["Sí", "No"], index=0)
        fotos_urls = st.text_area("Fotos URLs (separa por ; o salto de línea)",height=80)

        pros = st.text_area("Pros", height=90)
        contras = st.text_area("Contras", height=90)
        notas = st.text_area("Notas", height=70)

        c1, c2 = st.columns(2)
        with c1:
            flag_tren = st.checkbox("Flag: tren/ruido")
            flag_loft = st.checkbox("Flag: loft sin recámara")
        with c2:
            flag_fuera = st.checkbox("Flag: fuera de presupuesto")
            flag_pocos = st.checkbox("Flag: pocos deptos")

        submitted = st.form_submit_button("Agregar")
        if submitted:
            if not nombre.strip():
                st.error("Falta nombre.")
            elif m2 <= 0:
                st.error("m² construcción debe ser > 0.")
            else:
                base = st.session_state.df
                next_id = int(base["id"].max()) + 1 if base["id"].notna().any() else 1
                row = {
                    "id": next_id,
                    "nombre": nombre.strip(),
                    "zona_colonia": zona.strip() if zona else None,
                    "fuente": fuente,
                    "url": url.strip() if url else None,
                    "precio_mxn": float(precio) if precio else None,
                    "m2_construccion": float(m2),
                    "recamaras": int(rec),
                    "banos": int(ban),
                    "estacionamientos": int(est),
                    "tipo": tipo.strip() if tipo else None,
                    "nuevo": nuevo,
                    "fotos_urls": fotos_urls.strip() if fotos_urls else None,
                    "pros": pros.strip() if pros else None,
                    "contras": contras.strip() if contras else None,
                    "notas": notas.strip() if notas else None,
                    "flag_tren_ruido": bool(flag_tren),
                    "flag_loft_sin_rec": bool(flag_loft),
                    "flag_fuera_presupuesto": bool(flag_fuera),
                    "flag_pocos_deptos": bool(flag_pocos),
                    "decision_status": "Pendiente",
                    "decision_comentario": None,
                    "decision_quien": None,
                    "decision_fecha": None,
                    "precio_por_m2": None,
                }
                st.session_state.df = compute_fields(pd.concat([base, pd.DataFrame([row])], ignore_index=True))
                st.success("Agregado.")
                st.rerun()

st.subheader("Tabla (edita directo aquí)")
st.caption("Puedes editar celdas (incluye pros/contras). Luego exportas.")

editable_cols = [
    "id", "nombre", "zona_colonia", "fuente", "url",
    "precio_mxn", "m2_construccion", "recamaras", "banos", "estacionamientos",
    "tipo", "nuevo","fotos_urls",
    "pros", "contras", "notas",
    "flag_tren_ruido", "flag_loft_sin_rec", "flag_fuera_presupuesto", "flag_pocos_deptos",
]
edited = st.data_editor(
    st.session_state.df[editable_cols],
    use_container_width=True,
    num_rows="dynamic",
    key="editor",
)

# Keep schema + computed fields
df_out = ensure_schema(st.session_state.df.copy())
for c in edited.columns:
    df_out[c] = edited[c]
df_out = compute_fields(df_out)
st.session_state.df = df_out

c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    st.metric("Deptos", len(df_out))
with c2:
    st.metric("Pendientes", int((df_out["decision_status"] == "Pendiente").sum()))
with c3:
    st.caption(f"Última actualización: {now_str()}")

st.divider()
st.subheader("Exportar")
file_name = st.text_input("Nombre de archivo", value="deptos.xlsx")
if st.button("Generar Excel"):
    try:
        import io
        buffer = io.BytesIO()
        write_deptos_excel(df_out, buffer)
        buffer.seek(0)
        st.download_button(
            "Descargar Excel",
            data=buffer,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.success("Listo.")
    except Exception as e:
        st.error(f"Error exportando: {e}")