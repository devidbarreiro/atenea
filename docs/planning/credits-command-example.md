# Comando para Asignar Créditos

## Asignar 1000 créditos al usuario admin

```bash
python manage.py add_credits admin 1000 --description "Créditos iniciales"
```

## Otros ejemplos

### Asignar créditos con descripción personalizada
```bash
python manage.py add_credits username 500 --description "Créditos de promoción"
```

### Ver créditos de un usuario
```bash
python manage.py show_user_credits admin --detailed
```

### Resetear uso mensual de todos los usuarios
```bash
python manage.py reset_monthly_credits
```

### Ver qué se resetearía (dry-run)
```bash
python manage.py reset_monthly_credits --dry-run
```



