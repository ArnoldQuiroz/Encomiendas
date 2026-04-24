from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
from datetime import timedelta

from sistema.choices import EstadoGeneral, EstadoEnvio
from clientes.models import Cliente
from rutas.models import Ruta
from .validators import validar_peso_positivo, validar_codigo_encomienda
from .querysets import EncomiendaQuerySet

class Empleado(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cargo = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    estado = models.IntegerField(choices=EstadoGeneral.choices, default=EstadoGeneral.ACTIVO)
    fecha_ingreso = models.DateField()
    rutas_asignadas = models.ManyToManyField(Ruta, blank=True, related_name='empleados_asignados')

    def __str__(self):
        return f'[{self.codigo}] {self.apellidos}, {self.nombres}'

    class Meta:
        db_table = 'empleados'
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'

class Encomienda(models.Model):
    objects = EncomiendaQuerySet.as_manager()

    codigo = models.CharField(max_length=20, unique=True, validators=[validar_codigo_encomienda])
    descripcion = models.TextField()
    peso_kg = models.DecimalField(max_digits=8, decimal_places=2, validators=[validar_peso_positivo])
    volumen_cm3 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    remitente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='envios_como_remitente')
    destinatario = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='envios_como_destinatario')
    ruta = models.ForeignKey(Ruta, on_delete=models.PROTECT, related_name='encomiendas')
    empleado_registro = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name='encomiendas_registradas')
    
    estado = models.CharField(max_length=2, choices=EstadoEnvio.choices, default=EstadoEnvio.PENDIENTE)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_entrega_est = models.DateField(null=True, blank=True)
    fecha_entrega_real = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)

    # --- VALIDACIONES (Evitar datos basura) ---
    def clean(self):
        errors = {}
        if self.remitente_id and self.destinatario_id and self.remitente_id == self.destinatario_id:
            errors['destinatario'] = ValidationError('El destinatario no puede ser el mismo que el remitente.')
        if self.fecha_entrega_est and self.fecha_entrega_est < timezone.now().date():
            errors['fecha_entrega_est'] = ValidationError('La fecha de entrega estimada no puede ser en el pasado.')
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # --- PROPERTIES (Campos calculados al vuelo) ---
    @property
    def esta_entregada(self):
        return self.estado == EstadoEnvio.ENTREGADO

    @property
    def tiene_retraso(self):
        if not self.fecha_entrega_est or self.esta_entregada:
            return False
        return timezone.now().date() > self.fecha_entrega_est

    # --- LÓGICA DE NEGOCIO (Fat Models) ---
    def calcular_costo(self):
        PRECIO_POR_KG_EXTRA = 2.50
        PESO_BASE = 5.0
        costo = float(self.ruta.precio_base)
        if float(self.peso_kg) > PESO_BASE:
            costo += (float(self.peso_kg) - PESO_BASE) * PRECIO_POR_KG_EXTRA
        return round(costo, 2)

    def cambiar_estado(self, nuevo_estado, empleado, observacion=''):
        if nuevo_estado == self.estado:
            raise ValueError(f'La encomienda ya se encuentra en estado {self.get_estado_display()}')
        
        estado_anterior = self.estado
        self.estado = nuevo_estado
        if nuevo_estado == EstadoEnvio.ENTREGADO:
            self.fecha_entrega_real = timezone.now().date()
        self.save()

        HistorialEstado.objects.create(
            encomienda=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            empleado=empleado,
            observacion=observacion
        )
        return self

    @classmethod
    def crear_con_costo_calculado(cls, remitente, destinatario, ruta, empleado, descripcion, peso_kg, **kwargs):
        codigo = f'ENC-{timezone.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}'
        fecha_est = timezone.now().date() + timedelta(days=ruta.dias_entrega)
        
        encomienda = cls(
            codigo=codigo, descripcion=descripcion, peso_kg=peso_kg,
            remitente=remitente, destinatario=destinatario, ruta=ruta,
            empleado_registro=empleado, fecha_entrega_est=fecha_est,
            costo_envio=0, **kwargs
        )
        encomienda.costo_envio = encomienda.calcular_costo()
        encomienda.save()
        return encomienda

    def __str__(self):
        return f'[{self.codigo}] - {self.get_estado_display()}'

    class Meta:
        db_table = 'encomiendas'
        verbose_name = 'Encomienda'
        verbose_name_plural = 'Encomiendas'
        ordering = ['-fecha_registro']

class HistorialEstado(models.Model):
    encomienda = models.ForeignKey(Encomienda, on_delete=models.CASCADE, related_name='historial')
    estado_anterior = models.CharField(max_length=2, choices=EstadoEnvio.choices)
    estado_nuevo = models.CharField(max_length=2, choices=EstadoEnvio.choices)
    observacion = models.TextField(blank=True, null=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name='cambios_estado')
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_estados'
        ordering = ['-fecha_cambio']