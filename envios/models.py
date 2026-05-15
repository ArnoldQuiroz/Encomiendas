# envios/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
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
    estado = models.IntegerField(
        choices=EstadoGeneral.choices,
        default=EstadoGeneral.ACTIVO
    )
    fecha_ingreso = models.DateField()

    def __str__(self):
        return f'{self.codigo} - {self.apellidos}, {self.nombres}'

    class Meta:
        db_table = 'empleados'
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['apellidos']


class Encomienda(models.Model):
    objects = EncomiendaQuerySet.as_manager()
    codigo = models.CharField(
        max_length=20,
        unique=True,
        validators=[validar_codigo_encomienda]
    )
    descripcion = models.TextField()
    peso_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[
            validar_peso_positivo,
            MinValueValidator(0.01, message='El peso mínimo es 0.01 kg')
        ]
    )
    volumen_cm3 = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )

    # Relaciones
    remitente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        related_name='envios_como_remitente'
    )
    destinatario = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        related_name='envios_como_destinatario'
    )
    ruta = models.ForeignKey(
        Ruta, on_delete=models.PROTECT,
        related_name='encomiendas'
    )
    empleado_registro = models.ForeignKey(
        Empleado, on_delete=models.PROTECT,
        related_name='encomiendas_registradas'
    )

    # Estado y fechas
    estado = models.CharField(
        max_length=2,
        choices=EstadoEnvio.choices,
        default=EstadoEnvio.PENDIENTE
    )
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_entrega_est = models.DateField(null=True, blank=True)
    fecha_entrega_real = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)

    # 🏷️ Etiquetas separadas por coma (FRAGIL,PRIORITARIO,REFRIGERADO,PAGO_DESTINO)
    tags = models.CharField(max_length=200, blank=True, default='',
                            help_text='Etiquetas separadas por coma')

    # 💳 Información de pago
    ESTADO_PAGO = [
        ('PEN', 'Pendiente'),
        ('PAG', 'Pagado'),
        ('DEV', 'Devuelto'),
    ]
    METODO_PAGO = [
        ('EFE', 'Efectivo'),
        ('YAP', 'Yape'),
        ('PLI', 'Plin'),
        ('TRF', 'Transferencia'),
        ('TAR', 'Tarjeta'),
        ('CTR', 'Contra entrega'),
    ]
    estado_pago = models.CharField(max_length=3, choices=ESTADO_PAGO, default='PEN')
    metodo_pago = models.CharField(max_length=3, choices=METODO_PAGO, blank=True, default='')
    fecha_pago = models.DateTimeField(null=True, blank=True)
    cupon_aplicado = models.ForeignKey(
        'Cupon', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='encomiendas_usadas'
    )
    descuento_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    TAG_INFO = {
        'FRAGIL':       {'label': 'Frágil',         'icon': 'fa-wine-glass', 'color': '#ef4444', 'bg': '#fee2e2'},
        'PRIORITARIO':  {'label': 'Prioritario',    'icon': 'fa-star',       'color': '#f59e0b', 'bg': '#fef3c7'},
        'REFRIGERADO':  {'label': 'Refrigerado',    'icon': 'fa-snowflake',  'color': '#06b6d4', 'bg': '#cffafe'},
        'PAGO_DESTINO': {'label': 'Pago en destino','icon': 'fa-money-bill', 'color': '#059669', 'bg': '#d1fae5'},
        'DOCUMENTO':    {'label': 'Documento',      'icon': 'fa-file-alt',   'color': '#6366f1', 'bg': '#e0e7ff'},
    }

    @property
    def tags_list(self):
        """Devuelve los tags como lista, sin vacíos."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    @property
    def tags_info(self):
        """Lista de dicts con la info visual de cada tag."""
        return [
            {'codigo': t, **self.TAG_INFO[t]}
            for t in self.tags_list
            if t in self.TAG_INFO
        ]

    def __str__(self):
        return f'{self.codigo} [{self.get_estado_display()}]'

    # ====== PROPERTIES ======
    @property
    def esta_entregada(self):
        return self.estado == EstadoEnvio.ENTREGADO

    @property
    def esta_en_transito(self):
        return self.estado == EstadoEnvio.EN_TRANSITO

    @property
    def dias_en_transito(self):
        if not self.fecha_registro:
            return 0
        delta = timezone.now().date() - self.fecha_registro.date()
        return delta.days

    @property
    def tiene_retraso(self):
        if not self.fecha_entrega_est or self.esta_entregada:
            return False
        return timezone.now().date() > self.fecha_entrega_est

    @property
    def descripcion_corta(self):
        if len(self.descripcion) > 50:
            return self.descripcion[:50] + '...'
        return self.descripcion

    # ====== VALIDACIONES CRUZADAS ======
    def clean(self):
        errors = {}

        # Regla 1: remitente y destinatario diferentes
        if self.remitente_id and self.destinatario_id:
            if self.remitente_id == self.destinatario_id:
                errors['destinatario'] = ValidationError(
                    'El destinatario no puede ser el mismo que el remitente.'
                )

        # Regla 2: fecha de entrega no en el pasado
        # Solo se valida al CREAR (para no bloquear updates de registros antiguos
        # cuya fecha estimada ya quedó atrás).
        if self._state.adding and self.fecha_entrega_est:
            if self.fecha_entrega_est < timezone.now().date():
                errors['fecha_entrega_est'] = ValidationError(
                    'La fecha de entrega estimada no puede ser en el pasado.'
                )

        # Regla 3: fecha entrega real >= estimada
        if self.fecha_entrega_est and self.fecha_entrega_real:
            if self.fecha_entrega_real < self.fecha_entrega_est:
                errors['fecha_entrega_real'] = ValidationError(
                    'La fecha de entrega real no puede ser antes de la estimada.'
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Auto-generar el código si viene vacío (admin + form web)
        if not self.codigo:
            import uuid
            self.codigo = f'ENC-{timezone.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}'

        # Auto-calcular costo si viene en 0 y hay ruta + peso
        if (self.costo_envio is None or self.costo_envio == 0) and self.ruta_id and self.peso_kg:
            self.costo_envio = self.calcular_costo()

        # full_clean() ejecuta clean() + valida campos individuales.
        # Las reglas dependientes del tiempo solo se aplican al crear (ver clean()).
        self.full_clean()
        super().save(*args, **kwargs)

    # ====== MÉTODOS DE NEGOCIO ======
    def cambiar_estado(self, nuevo_estado, empleado, observacion=''):
        if nuevo_estado == self.estado:
            raise ValueError(
                f'La encomienda ya está en estado {self.get_estado_display()}'
            )

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

        # 📧 Notificación por email (best-effort, no rompe el flujo)
        try:
            from .notificaciones import notificar_cambio_estado
            notificar_cambio_estado(self, estado_anterior)
        except Exception:
            pass

        return self

    def calcular_costo(self):
        PRECIO_POR_KG_EXTRA = 2.50
        PESO_BASE = 5.0
        costo = float(self.ruta.precio_base)
        if float(self.peso_kg) > PESO_BASE:
            costo += (float(self.peso_kg) - PESO_BASE) * PRECIO_POR_KG_EXTRA
        return round(costo, 2)

    @classmethod
    def crear_con_costo_calculado(cls, remitente, destinatario, ruta,
                                   empleado, descripcion, peso_kg, **kwargs):
        import uuid
        from datetime import timedelta

        codigo = f'ENC-{timezone.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}'
        fecha_est = timezone.now().date() + timedelta(days=ruta.dias_entrega)

        encomienda = cls(
            codigo=codigo,
            descripcion=descripcion,
            peso_kg=peso_kg,
            remitente=remitente,
            destinatario=destinatario,
            ruta=ruta,
            empleado_registro=empleado,
            fecha_entrega_est=fecha_est,
            costo_envio=0,
            **kwargs
        )
        encomienda.costo_envio = encomienda.calcular_costo()
        encomienda.save()
        return encomienda

    class Meta:
        db_table = 'encomiendas'
        verbose_name = 'Encomienda'
        verbose_name_plural = 'Encomiendas'
        ordering = ['-fecha_registro']


class Cupon(models.Model):
    """🎟️ Cupones de descuento aplicables a envíos."""
    TIPO_PORCENTAJE = 'PCT'
    TIPO_FIJO = 'FIJ'
    TIPOS = [
        (TIPO_PORCENTAJE, 'Porcentaje (%)'),
        (TIPO_FIJO,       'Monto fijo (S/)'),
    ]

    codigo = models.CharField(max_length=20, unique=True,
                              help_text='Código único (ej: VERANO2026)')
    descripcion = models.CharField(max_length=200, blank=True, default='')
    tipo = models.CharField(max_length=3, choices=TIPOS, default=TIPO_PORCENTAJE)
    valor = models.DecimalField(max_digits=10, decimal_places=2,
                                help_text='Porcentaje (1-100) o monto en S/')
    usos_maximos = models.PositiveIntegerField(default=0,
                                                help_text='0 = ilimitado')
    usos_actuales = models.PositiveIntegerField(default=0)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cupones'
        ordering = ['-creado_en']

    def __str__(self):
        return f'{self.codigo} ({self.get_tipo_display()} {self.valor})'

    @property
    def valido(self):
        """Verifica si el cupón es válido para usarse hoy."""
        from django.utils import timezone
        if not self.activo:
            return False
        if self.usos_maximos and self.usos_actuales >= self.usos_maximos:
            return False
        hoy = timezone.now().date()
        if self.fecha_inicio and hoy < self.fecha_inicio:
            return False
        if self.fecha_fin and hoy > self.fecha_fin:
            return False
        return True

    def calcular_descuento(self, monto):
        """Calcula el descuento sobre un monto dado."""
        from decimal import Decimal
        monto = Decimal(str(monto))
        valor = Decimal(str(self.valor))
        if self.tipo == self.TIPO_PORCENTAJE:
            return (monto * valor / Decimal('100')).quantize(Decimal('0.01'))
        return min(valor, monto)


class Tarea(models.Model):
    """✅ Tareas/recordatorios del operador."""
    PRIORIDAD_BAJA = 'BAJA'
    PRIORIDAD_MEDIA = 'MEDIA'
    PRIORIDAD_ALTA = 'ALTA'
    PRIORIDADES = [
        (PRIORIDAD_BAJA,  'Baja'),
        (PRIORIDAD_MEDIA, 'Media'),
        (PRIORIDAD_ALTA,  'Alta'),
    ]

    usuario = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE,
        related_name='tareas'
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default=PRIORIDAD_MEDIA)
    fecha_limite = models.DateField(null=True, blank=True)
    completada = models.BooleanField(default=False)
    encomienda = models.ForeignKey(
        'Encomienda', on_delete=models.SET_NULL,
        related_name='tareas', null=True, blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_completada = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tareas'
        ordering = ['completada', '-prioridad', 'fecha_limite']

    def __str__(self):
        return self.titulo

    @property
    def vencida(self):
        from django.utils import timezone
        if self.completada or not self.fecha_limite:
            return False
        return self.fecha_limite < timezone.now().date()


class EncomiendaFavorita(models.Model):
    """⭐ Encomiendas marcadas como favoritas por cada usuario."""
    usuario = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE,
        related_name='favoritas'
    )
    encomienda = models.ForeignKey(
        'Encomienda', on_delete=models.CASCADE,
        related_name='favoritos'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'encomienda_favoritas'
        unique_together = [('usuario', 'encomienda')]
        ordering = ['-fecha']


class ComentarioInterno(models.Model):
    """💬 Notas internas entre operadores (no visibles para el cliente)."""
    encomienda = models.ForeignKey(
        'Encomienda', on_delete=models.CASCADE,
        related_name='comentarios'
    )
    empleado = models.ForeignKey(
        Empleado, on_delete=models.PROTECT,
        related_name='comentarios_internos'
    )
    contenido = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    importante = models.BooleanField(default=False)

    class Meta:
        db_table = 'comentarios_internos'
        ordering = ['-fecha']
        verbose_name = 'Comentario interno'
        verbose_name_plural = 'Comentarios internos'

    def __str__(self):
        return f'{self.empleado} en {self.encomienda.codigo}'


class HistorialEstado(models.Model):
    encomienda = models.ForeignKey(
        Encomienda, on_delete=models.CASCADE,
        related_name='historial'
    )
    estado_anterior = models.CharField(max_length=2, choices=EstadoEnvio.choices)
    estado_nuevo = models.CharField(max_length=2, choices=EstadoEnvio.choices)
    observacion = models.TextField(blank=True, null=True)
    empleado = models.ForeignKey(
        Empleado, on_delete=models.PROTECT,
        related_name='cambios_estado'
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.encomienda.codigo}: {self.estado_anterior}→{self.estado_nuevo}'

    class Meta:
        db_table = 'historial_estados'
        ordering = ['-fecha_cambio']