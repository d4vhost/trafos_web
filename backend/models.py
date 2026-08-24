from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Incidencia(Base):
    """Modelo para la tabla de incidencias, gestionando datos de ADMS."""
    __tablename__ = "incidencias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estado = Column(String)
    prioridad = Column(String)
    incidencia = Column(String, unique=True)
    num_transf = Column(String)
    potencia_transf = Column(String)
    tipo = Column(String)
    trabajo_adicional = Column(Text)
    observaciones = Column(Text)
    grupo = Column(String)
    wr = Column(String)
    orden_bodega = Column(String)
    fecha_interrupcion = Column(String)
    fecha_planificado = Column(String)
    hora_planificado = Column(String)
    alimentador_actual = Column(String)
    coordenadas = Column(String)
    id_medidor = Column(String)
    causa = Column(String)
    subcausa = Column(String)
    alimentador_normal = Column(String)
    atr = Column(String)
    cuadrillas = Column(String)
    afectados = Column(String)

    # Extra fields from PDF
    estado_adms = Column(String)
    subtipo = Column(String)
    etr = Column(String)
    estado_energia = Column(String)
    llamadas_count = Column(String)
    creado_en = Column(String)
    creado_por = Column(String)
    instruccion = Column(String)
    dispositivo_nombre = Column(String)
    dispositivo_tipo = Column(String)
    loc_red = Column(String)
    componente_fallo = Column(String)
    tipo_construccion = Column(String)
    comentarios_resolucion = Column(Text)
    llamadas_detalle = Column(Text)
    cmi = Column(String)
    potencia_afectados_kw = Column(String)
    pdf_filename = Column(String)
    fecha_procesado = Column(String)
    es_trabajo_adicional = Column(Boolean, default=False)
    tipo_cuadrilla = Column(String)

    # Relaciones
    analizadores = relationship("Analizador", back_populates="incidencia_rel")
    gis_entries = relationship("GISEntry", back_populates="incidencia_rel")

    def __repr__(self):
        return f"<Incidencia(incidencia='{self.incidencia}', estado='{self.estado}')>"


class Analizador(Base):
    """Modelo para la tabla de analizadores."""
    __tablename__ = "analizadores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analizado = Column(String)
    fecha_instalacion = Column(String)
    fecha_retiro = Column(String)
    inc = Column(String, ForeignKey("incidencias.incidencia"))
    trafo = Column(String)
    potencia = Column(String)
    tipo = Column(String)
    alimentador = Column(String)
    resp_instalacion = Column(String)
    resp_retiro = Column(String)
    observacion = Column(Text)

    incidencia_rel = relationship("Incidencia", back_populates="analizadores")

    def __repr__(self):
        return f"<Analizador(id={self.id}, analizado='{self.analizado}')>"


class GISEntry(Base):
    """Modelo para entradas en el sistema GIS."""
    __tablename__ = "gis_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estado = Column(String)
    tarea = Column(Text)
    tipo = Column(String)
    antiguo_trafo = Column(String)
    antiguo_potencia = Column(String)
    nuevo_trafo = Column(String)
    nuevo_potencia = Column(String)
    poste_nuevo = Column(String)
    fecha_realizacion = Column(String)
    inc = Column(String, ForeignKey("incidencias.incidencia"))
    documento = Column(String)
    observacion = Column(Text)

    incidencia_rel = relationship("Incidencia", back_populates="gis_entries")

    def __repr__(self):
        return f"<GISEntry(id={self.id}, estado='{self.estado}')>"


class Eventual(Base):
    """Modelo para la tabla de eventuales."""
    __tablename__ = "eventuales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_instalacion = Column(String)
    fecha_evento = Column(String)
    fecha_retiro = Column(String)
    direccion = Column(String)
    poste = Column(String)
    trafo = Column(String)
    potencia = Column(String)
    tipo = Column(String)
    responsable_instalacion = Column(String)
    responsable_retiro = Column(String)
    alimentador = Column(String)
    tramite = Column(String)
    documento = Column(String)
    observacion = Column(Text)

    def __repr__(self):
        return f"<Eventual(id={self.id}, tramite='{self.tramite}')>"


class Bodega(Base):
    """Modelo para control de bodega y materiales."""
    __tablename__ = "bodega"

    id = Column(Integer, primary_key=True, autoincrement=True)
    retirado = Column(String)
    anio = Column(String)
    id_evento = Column(String)
    evento = Column(String)
    bodega_num = Column(String)
    id_orden = Column(String)
    partida = Column(String)
    codigo_rapido = Column(String)
    cuenta_contable = Column(String)
    etapa_funcional = Column(String)
    observaciones = Column(Text)
    para_uso = Column(Text)
    codigo = Column(String)
    nombre_material = Column(String)
    cantidad = Column(String)
    disponible = Column(String)
    abreviatura = Column(String)

    def __repr__(self):
        return f"<Bodega(id={self.id}, codigo='{self.codigo}', nombre_material='{self.nombre_material}')>"
