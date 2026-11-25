"""auditoria fases 4 y 5: seguridad (token_version, codigo hasheado),
integridad (checks, unico por finca, idempotencia de sync) e indices/ondelete
explicito en las 29 FK existentes

Revision ID: 7a2f9c4e5b10
Revises: 4445bc83d5ed
Create Date: 2026-11-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a2f9c4e5b10'
down_revision = '4445bc83d5ed'
branch_labels = None
depends_on = None


# (tabla, columna, nombre_constraint_actual, tabla_referenciada, col_referenciada, necesita_indice)
FKS = [
    ("balances_industriales", "pronostico_id", "balances_industriales_pronostico_id_fkey", "pronosticos_produccion", "id", True),
    ("balances_industriales", "usuario_id", "balances_industriales_usuario_id_fkey", "usuarios", "id", True),
    ("ciclos_cosecha", "lote_id", "ciclos_cosecha_lote_id_fkey", "lotes", "id", True),
    ("compradores", "usuario_id", "compradores_usuario_id_fkey", "usuarios", "id", False),
    ("contenidos_mensajes", "actualizado_por", "contenidos_mensajes_actualizado_por_fkey", "usuarios", "id", True),
    ("estados_vias", "actualizado_por", "estados_vias_actualizado_por_fkey", "usuarios", "id", True),
    ("fincas", "usuario_id", "fincas_usuario_id_fkey", "usuarios", "id", True),
    ("lotes", "finca_id", "lotes_finca_id_fkey", "fincas", "id", True),
    ("notificaciones", "ciclo_cosecha_id", "fk_notificaciones_ciclo_cosecha_id", "ciclos_cosecha", "id", True),
    ("notificaciones", "lote_id", "fk_notificaciones_lote_id", "lotes", "id", True),
    ("notificaciones", "usuario_id", "notificaciones_usuario_id_fkey", "usuarios", "id", True),
    ("password_reset_tokens", "usuario_id", "password_reset_tokens_usuario_id_fkey", "usuarios", "id", True),
    ("precios", "comprador_id", "precios_comprador_id_fkey", "compradores", "id", True),
    ("pronosticos_produccion", "lote_id", "pronosticos_produccion_lote_id_fkey", "lotes", "id", True),
    ("pronosticos_produccion", "registro_produccion_id", "fk_pronosticos_produccion_registro_produccion_id", "registros_produccion", "id", True),
    ("publicaciones_mercado", "lote_id", "publicaciones_mercado_lote_id_fkey", "lotes", "id", True),
    ("publicaciones_mercado", "palmicultor_id", "publicaciones_mercado_palmicultor_id_fkey", "usuarios", "id", True),
    ("registros_polinizacion", "lote_id", "registros_polinizacion_lote_id_fkey", "lotes", "id", True),
    ("registros_produccion", "lote_id", "registros_produccion_lote_id_fkey", "lotes", "id", True),
    ("sms_ussd_logs", "usuario_id", "sms_ussd_logs_usuario_id_fkey", "usuarios", "id", True),
    ("solicitudes_transporte", "comprador_id", "solicitudes_transporte_comprador_id_fkey", "compradores", "id", True),
    ("solicitudes_transporte", "finca_id", "solicitudes_transporte_finca_id_fkey", "fincas", "id", True),
    ("solicitudes_transporte", "lote_id", "solicitudes_transporte_lote_id_fkey", "lotes", "id", True),
    ("solicitudes_transporte", "palmicultor_id", "solicitudes_transporte_palmicultor_id_fkey", "usuarios", "id", True),
    ("solicitudes_transporte", "transportador_id", "solicitudes_transporte_transportador_id_fkey", "transportadores", "id", True),
    ("solicitudes_transporte", "vehiculo_id", "solicitudes_transporte_vehiculo_id_fkey", "vehiculos", "id", True),
    ("transportadores", "usuario_id", "transportadores_usuario_id_fkey", "usuarios", "id", False),
    ("ussd_sesiones", "usuario_id", "ussd_sesiones_usuario_id_fkey", "usuarios", "id", True),
    ("vehiculos", "transportador_id", "vehiculos_transportador_id_fkey", "transportadores", "id", True),
]


def upgrade():
    # --- DEV-F4-02/03: revocación de sesión ---------------------------------
    op.add_column(
        "usuarios",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )

    # --- DEV-F4-04: código de recuperación hasheado -------------------------
    # String(6) -> String(255) para guardar el hash en vez del código en claro.
    op.alter_column(
        "password_reset_tokens", "codigo", existing_type=sa.String(length=6), type_=sa.String(length=255)
    )

    # --- F5-01: idempotencia de la sincronización de producción -------------
    op.add_column("registros_produccion", sa.Column("creado_por_id", sa.Integer(), nullable=True))
    op.add_column("registros_produccion", sa.Column("client_local_id", sa.String(length=100), nullable=True))
    op.create_index(
        op.f("ix_registros_produccion_creado_por_id"), "registros_produccion", ["creado_por_id"]
    )
    op.create_unique_constraint(
        "uq_registros_produccion_creado_por_local_id",
        "registros_produccion",
        ["creado_por_id", "client_local_id"],
    )

    # --- F5-06: interés de compra sobre una publicación ---------------------
    op.create_table(
        "intereses_comprador",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("publicacion_id", sa.Integer(), nullable=False),
        sa.Column("comprador_id", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=True),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.Column("fecha", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publicacion_id", "comprador_id", name="uq_intereses_publicacion_comprador"),
    )
    op.create_index(
        op.f("ix_intereses_comprador_publicacion_id"), "intereses_comprador", ["publicacion_id"]
    )
    op.create_index(op.f("ix_intereses_comprador_comprador_id"), "intereses_comprador", ["comprador_id"])
    op.create_foreign_key(
        "intereses_comprador_publicacion_id_fkey",
        "intereses_comprador",
        "publicaciones_mercado",
        ["publicacion_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "intereses_comprador_comprador_id_fkey",
        "intereses_comprador",
        "compradores",
        ["comprador_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # --- F5-05: código de lote único por finca -------------------------------
    # Renombra duplicados existentes antes de crear la restricción, para que
    # la migración no falle contra una base con datos reales que ya los tenga.
    op.execute(
        """
        WITH duplicados AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY finca_id, codigo ORDER BY id
            ) AS rn
            FROM lotes
        )
        UPDATE lotes
        SET codigo = lotes.codigo || '-DUP' || duplicados.id
        FROM duplicados
        WHERE lotes.id = duplicados.id AND duplicados.rn > 1
        """
    )
    op.create_unique_constraint("uq_lotes_finca_codigo", "lotes", ["finca_id", "codigo"])

    # --- F5-04: dominios positivos -------------------------------------------
    op.create_check_constraint(
        "ck_fincas_area_positiva", "fincas", "area_hectareas IS NULL OR area_hectareas > 0"
    )
    op.create_check_constraint(
        "ck_lotes_area_positiva", "lotes", "area_hectareas IS NULL OR area_hectareas > 0"
    )
    op.create_check_constraint(
        "ck_vehiculos_capacidad_positiva",
        "vehiculos",
        "capacidad_toneladas IS NULL OR capacidad_toneladas > 0",
    )

    # --- F5-09/F5-10: índice y ON DELETE explícito en las 29 FK existentes --
    for tabla, columna, nombre_constraint, tabla_ref, col_ref, necesita_indice in FKS:
        op.drop_constraint(nombre_constraint, tabla, type_="foreignkey")
        op.create_foreign_key(
            nombre_constraint, tabla, tabla_ref, [columna], [col_ref], ondelete="RESTRICT"
        )
        if necesita_indice:
            op.create_index(op.f(f"ix_{tabla}_{columna}"), tabla, [columna])


def downgrade():
    for tabla, columna, nombre_constraint, tabla_ref, col_ref, necesita_indice in reversed(FKS):
        if necesita_indice:
            op.drop_index(op.f(f"ix_{tabla}_{columna}"), table_name=tabla)
        op.drop_constraint(nombre_constraint, tabla, type_="foreignkey")
        op.create_foreign_key(nombre_constraint, tabla, tabla_ref, [columna], [col_ref])

    op.drop_constraint("ck_vehiculos_capacidad_positiva", "vehiculos", type_="check")
    op.drop_constraint("ck_lotes_area_positiva", "lotes", type_="check")
    op.drop_constraint("ck_fincas_area_positiva", "fincas", type_="check")

    op.drop_constraint("uq_lotes_finca_codigo", "lotes", type_="unique")

    op.drop_constraint("intereses_comprador_comprador_id_fkey", "intereses_comprador", type_="foreignkey")
    op.drop_constraint("intereses_comprador_publicacion_id_fkey", "intereses_comprador", type_="foreignkey")
    op.drop_index(op.f("ix_intereses_comprador_comprador_id"), table_name="intereses_comprador")
    op.drop_index(op.f("ix_intereses_comprador_publicacion_id"), table_name="intereses_comprador")
    op.drop_table("intereses_comprador")

    op.drop_constraint(
        "uq_registros_produccion_creado_por_local_id", "registros_produccion", type_="unique"
    )
    op.drop_index(op.f("ix_registros_produccion_creado_por_id"), table_name="registros_produccion")
    op.drop_column("registros_produccion", "client_local_id")
    op.drop_column("registros_produccion", "creado_por_id")

    op.alter_column(
        "password_reset_tokens", "codigo", existing_type=sa.String(length=255), type_=sa.String(length=6)
    )

    op.drop_column("usuarios", "token_version")
