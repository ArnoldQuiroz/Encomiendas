from rest_framework import serializers
from .models import Encomienda, HistorialEstado, Empleado
from clientes.models import Cliente
from rutas.models import Ruta


# ════════════════════════════════════════════════════════════
# SESIÓN 06 — Tema 1: Serializer dinámico
# Permite filtrar campos desde la vista o el request
# Uso: EncomiendaListSerializer(instance, fields=['id','codigo'])
# ════════════════════════════════════════════════════════════
class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)
        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


# ════════════════════════════════════════════════════════════
# SESIÓN 06 — Tema 2: Serializer básico (serializers.Serializer)
# No usa ModelSerializer — define cada campo manualmente
# Útil para endpoints que no mapean 1:1 con un modelo
# ════════════════════════════════════════════════════════════
class ResumenEncomiendaSerializer(serializers.Serializer):
    codigo       = serializers.CharField(read_only=True)
    estado       = serializers.CharField(read_only=True)
    peso_kg      = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    costo_envio  = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    ruta_nombre  = serializers.SerializerMethodField()
    tiene_retraso = serializers.BooleanField(read_only=True)

    def get_ruta_nombre(self, obj):
        return f"{obj.ruta.origen} → {obj.ruta.destino}" if obj.ruta else ''


# ════════════════════════════════════════════════════════════
# Serializers de modelos relacionados
# ════════════════════════════════════════════════════════════
class ClienteSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.ReadOnlyField()
    esta_activo     = serializers.ReadOnlyField()

    class Meta:
        model  = Cliente
        fields = [
            'id', 'tipo_doc', 'nro_doc',
            'nombres', 'apellidos', 'nombre_completo',
            'telefono', 'email', 'esta_activo',
        ]


class RutaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Ruta
        fields = ['id', 'codigo', 'origen', 'destino', 'precio_base', 'dias_entrega', 'estado']


# SESIÓN 06 — Tema 3: EmpleadoSerializer
class EmpleadoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model  = Empleado
        fields = ['id', 'codigo', 'nombres', 'apellidos', 'nombre_completo',
                  'cargo', 'email', 'telefono', 'estado', 'fecha_ingreso']
        read_only_fields = ['codigo']

    def get_nombre_completo(self, obj):
        return f"{obj.apellidos}, {obj.nombres}"

    def validate_email(self, value):
        qs = Empleado.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un empleado con este email.')
        return value


class HistorialEstadoSerializer(serializers.ModelSerializer):
    empleado_nombre      = serializers.ReadOnlyField(source='empleado.__str__')
    estado_anterior_display = serializers.CharField(source='get_estado_anterior_display', read_only=True)
    estado_nuevo_display    = serializers.CharField(source='get_estado_nuevo_display',    read_only=True)

    class Meta:
        model  = HistorialEstado
        fields = [
            'id', 'estado_anterior', 'estado_anterior_display',
            'estado_nuevo', 'estado_nuevo_display',
            'empleado_nombre', 'observacion', 'fecha_cambio',
        ]


# ════════════════════════════════════════════════════════════
# SESIÓN 06 — Tema 4: Serializer simplificado para listas
# Devuelve solo los campos esenciales (mejora rendimiento)
# ════════════════════════════════════════════════════════════
class EncomiendaListSerializer(DynamicFieldsModelSerializer):
    estado_display  = serializers.CharField(source='get_estado_display', read_only=True)
    remitente_nombre  = serializers.CharField(source='remitente.nombre_completo', read_only=True)
    destinatario_nombre = serializers.CharField(source='destinatario.nombre_completo', read_only=True)
    ruta_nombre     = serializers.SerializerMethodField()
    tiene_retraso   = serializers.ReadOnlyField()

    class Meta:
        model  = Encomienda
        fields = [
            'id', 'codigo', 'estado', 'estado_display',
            'remitente_nombre', 'destinatario_nombre', 'ruta_nombre',
            'peso_kg', 'costo_envio', 'fecha_registro',
            'fecha_entrega_est', 'tiene_retraso',
        ]

    def get_ruta_nombre(self, obj):
        return f"{obj.ruta.origen} → {obj.ruta.destino}" if obj.ruta else ''


# ════════════════════════════════════════════════════════════
# SESIÓN 06 — Tema 5: Serializer con validaciones personalizadas
# Serializer específico para CREAR encomiendas con reglas estrictas
# ════════════════════════════════════════════════════════════
class EncomiendaCreateSerializer(serializers.ModelSerializer):
    remitente_id    = serializers.PrimaryKeyRelatedField(queryset=Cliente.objects.activos(), source='remitente')
    destinatario_id = serializers.PrimaryKeyRelatedField(queryset=Cliente.objects.activos(), source='destinatario')
    ruta_id         = serializers.PrimaryKeyRelatedField(queryset=Ruta.objects.activas(), source='ruta')

    class Meta:
        model  = Encomienda
        fields = [
            'remitente_id', 'destinatario_id', 'ruta_id',
            'descripcion', 'peso_kg', 'volumen_cm3',
            'costo_envio', 'fecha_entrega_est', 'observaciones',
        ]

    def validate_peso_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError('El peso debe ser mayor a 0 kg.')
        if value > 1000:
            raise serializers.ValidationError('El peso no puede superar 1000 kg.')
        return value

    def validate_costo_envio(self, value):
        if value < 0:
            raise serializers.ValidationError('El costo de envío no puede ser negativo.')
        return value

    def validate_fecha_entrega_est(self, value):
        from django.utils import timezone
        if value and value < timezone.now().date():
            raise serializers.ValidationError('La fecha estimada no puede ser en el pasado.')
        return value

    def validate(self, data):
        remitente    = data.get('remitente')
        destinatario = data.get('destinatario')
        if remitente and destinatario and remitente == destinatario:
            raise serializers.ValidationError(
                {'destinatario_id': 'El remitente y el destinatario no pueden ser la misma persona.'}
            )
        return data


# ════════════════════════════════════════════════════════════
# Serializer completo (detalle + escritura con IDs)
# ════════════════════════════════════════════════════════════
class EncomiendaSerializer(serializers.ModelSerializer):
    esta_entregada  = serializers.ReadOnlyField()
    tiene_retraso   = serializers.ReadOnlyField()
    dias_en_transito = serializers.ReadOnlyField()
    descripcion_corta = serializers.ReadOnlyField()
    estado_display  = serializers.SerializerMethodField()

    class Meta:
        model  = Encomienda
        fields = [
            'id', 'codigo', 'descripcion', 'descripcion_corta',
            'peso_kg', 'volumen_cm3', 'costo_envio',
            'remitente', 'destinatario', 'ruta', 'empleado_registro',
            'estado', 'estado_display',
            'fecha_registro', 'fecha_entrega_est', 'fecha_entrega_real',
            'esta_entregada', 'tiene_retraso', 'dias_en_transito',
            'observaciones',
        ]
        read_only_fields = ['codigo', 'fecha_registro', 'fecha_entrega_real']

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def validate_peso_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError('El peso debe ser mayor a 0 kg.')
        if value > 1000:
            raise serializers.ValidationError('El peso no puede superar los 1000 kg.')
        return value

    def validate_fecha_entrega_est(self, value):
        from django.utils import timezone
        if value and value < timezone.now().date():
            raise serializers.ValidationError('La fecha estimada no puede ser en el pasado.')
        return value

    def validate(self, data):
        remitente    = data.get('remitente')
        destinatario = data.get('destinatario')
        if remitente and destinatario and remitente == destinatario:
            raise serializers.ValidationError(
                'El remitente y el destinatario no pueden ser la misma persona.'
            )
        return data


class EncomiendaDetailSerializer(EncomiendaSerializer):
    remitente    = ClienteSerializer(read_only=True)
    destinatario = ClienteSerializer(read_only=True)
    ruta         = RutaSerializer(read_only=True)
    historial    = serializers.SerializerMethodField()

    remitente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(), write_only=True, source='remitente'
    )
    destinatario_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(), write_only=True, source='destinatario'
    )
    ruta_id = serializers.PrimaryKeyRelatedField(
        queryset=Ruta.objects.activas(), write_only=True, source='ruta'
    )

    class Meta(EncomiendaSerializer.Meta):
        fields = [
            'id', 'codigo', 'descripcion', 'peso_kg',
            'remitente', 'remitente_id',
            'destinatario', 'destinatario_id',
            'ruta', 'ruta_id',
            'estado', 'estado_display', 'costo_envio',
            'fecha_registro', 'fecha_entrega_est', 'fecha_entrega_real',
            'esta_entregada', 'tiene_retraso', 'dias_en_transito',
            'historial', 'observaciones',
        ]

    def get_historial(self, obj):
        return HistorialEstadoSerializer(obj.historial.all()[:5], many=True).data
