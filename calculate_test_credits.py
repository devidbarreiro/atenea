#!/usr/bin/env python
"""
Script para calcular cuántas pruebas se pueden realizar con 100€
100€ = 10,000 créditos Atenea (100 créditos = 1 USD)
"""
from decimal import Decimal

# Precios por servicio (copiados de credits.py)
PRICING = {
    'gemini_veo': {
        'video': 50,  # por segundo
        'video_audio': 75,  # por segundo (con audio)
    },
    'sora': {
        'sora-2': 10,  # por segundo
        'sora-2-pro': 50,  # por segundo
    },
    'heygen_avatar_v2': {
        'video': 5,  # por segundo
    },
    'heygen_avatar_iv': {
        'video': 15,  # por segundo
    },
    'vuela_ai': {
        'basic': 3,  # por segundo
        'premium': 5,  # por segundo
    },
    'gemini_image': {
        'image': 2,  # por imagen
    },
    'elevenlabs': {
        'per_character': Decimal('0.017'),  # por carácter
    },
    # Higgsfield (precios según documentación oficial)
    'higgsfield_dop_standard': {
        'video': 44,  # 7 créditos Higgsfield → ~$0.44 → 44 créditos Atenea
    },
    'higgsfield_dop_preview': {
        'video': 19,  # 3 créditos Higgsfield → ~$0.19 → 19 créditos Atenea
    },
    'higgsfield_seedance_v1_pro': {
        'video': 74,  # 400 créditos Higgsfield → ~$0.74 → 74 créditos Atenea
    },
    'higgsfield_kling_v2_1_pro': {
        'video': 45,  # 35 créditos Higgsfield → ~$0.45 → 45 créditos Atenea
    },
    # Higgsfield Text-to-Image
    'higgsfield_soul_standard': {
        'image': 2,  # 0.25 créditos Higgsfield → ~$0.023 → ~2 créditos Atenea
    },
    'reve_text_to_image': {
        'image': 1,  # 1 crédito Reve → ~$0.01 → ~1 crédito Atenea
    },
    'kling_v1': {
        'std_5s': 14,
        'std_10s': 28,
        'pro_5s': 49,
        'pro_10s': 98,
    },
    'kling_v1_5': {
        'std_5s': 28,
        'std_10s': 56,
        'pro_5s': 49,
        'pro_10s': 98,
    },
    'kling_v1_6': {
        'std_5s': 28,
        'std_10s': 56,
        'pro_5s': 49,
        'pro_10s': 98,
    },
    'kling_v2_master': {
        '5s': 140,
        '10s': 280,
    },
    'kling_v2_1': {
        'std_5s': 28,
        'std_10s': 56,
        'pro_5s': 49,
        'pro_10s': 98,
    },
    'kling_v2_5_turbo': {
        'std_5s': 21,
        'std_10s': 42,
        'pro_5s': 35,
        'pro_10s': 70,
    },
}

TOTAL_CREDITS = 10000  # 100€ = 10,000 créditos


def calculate_tests(credits_available, cost_per_test):
    """Calcula cuántas pruebas se pueden hacer con los créditos disponibles"""
    if cost_per_test == 0:
        return 0
    return int(credits_available / cost_per_test)


def format_cost(cost):
    """Formatea el costo en créditos y euros"""
    euros = float(cost) / 100
    return f"{cost} créditos (€{euros:.2f})"


def main():
    print("=" * 80)
    print("💰 CÁLCULO DE PRUEBAS DISPONIBLES CON 100€")
    print("=" * 80)
    print(f"\nCréditos disponibles: {TOTAL_CREDITS} créditos (€100.00)")
    print(f"Conversión: 100 créditos Atenea = 1 USD\n")
    
    print("=" * 80)
    print("📹 VIDEOS")
    print("=" * 80)
    
    # Videos por duración común (8 segundos)
    duration = 8
    
    scenarios = [
        # Gemini Veo
        ("Gemini Veo (8s, sin audio)", PRICING['gemini_veo']['video'] * duration),
        ("Gemini Veo (8s, con audio)", PRICING['gemini_veo']['video_audio'] * duration),
        ("Gemini Veo (10s, sin audio)", PRICING['gemini_veo']['video'] * 10),
        ("Gemini Veo (10s, con audio)", PRICING['gemini_veo']['video_audio'] * 10),
        
        # Sora
        ("Sora 2 (8s)", PRICING['sora']['sora-2'] * duration),
        ("Sora 2 (10s)", PRICING['sora']['sora-2'] * 10),
        ("Sora 2 Pro (8s)", PRICING['sora']['sora-2-pro'] * duration),
        ("Sora 2 Pro (10s)", PRICING['sora']['sora-2-pro'] * 10),
        
        # HeyGen
        ("HeyGen Avatar v2 (8s)", PRICING['heygen_avatar_v2']['video'] * duration),
        ("HeyGen Avatar v2 (10s)", PRICING['heygen_avatar_v2']['video'] * 10),
        ("HeyGen Avatar IV (8s)", PRICING['heygen_avatar_iv']['video'] * duration),
        ("HeyGen Avatar IV (10s)", PRICING['heygen_avatar_iv']['video'] * 10),
        
        # Vuela AI
        ("Vuela AI Basic (8s)", PRICING['vuela_ai']['basic'] * duration),
        ("Vuela AI Premium (8s)", PRICING['vuela_ai']['premium'] * duration),
        
        # Higgsfield
        ("Higgsfield DOP Preview", PRICING['higgsfield_dop_preview']['video']),
        ("Higgsfield DOP Standard", PRICING['higgsfield_dop_standard']['video']),
        ("Higgsfield Kling v2.1 Pro", PRICING['higgsfield_kling_v2_1_pro']['video']),
        ("Higgsfield Seedance v1 Pro", PRICING['higgsfield_seedance_v1_pro']['video']),
        
        # Kling
        ("Kling v1 Standard 5s", PRICING['kling_v1']['std_5s']),
        ("Kling v1 Standard 10s", PRICING['kling_v1']['std_10s']),
        ("Kling v1 Pro 5s", PRICING['kling_v1']['pro_5s']),
        ("Kling v1 Pro 10s", PRICING['kling_v1']['pro_10s']),
        ("Kling v1.5 Standard 5s", PRICING['kling_v1_5']['std_5s']),
        ("Kling v1.5 Standard 10s", PRICING['kling_v1_5']['std_10s']),
        ("Kling v1.5 Pro 5s", PRICING['kling_v1_5']['pro_5s']),
        ("Kling v1.5 Pro 10s", PRICING['kling_v1_5']['pro_10s']),
        ("Kling v1.6 Standard 5s", PRICING['kling_v1_6']['std_5s']),
        ("Kling v1.6 Standard 10s", PRICING['kling_v1_6']['std_10s']),
        ("Kling v1.6 Pro 5s", PRICING['kling_v1_6']['pro_5s']),
        ("Kling v1.6 Pro 10s", PRICING['kling_v1_6']['pro_10s']),
        ("Kling v2.1 Standard 5s", PRICING['kling_v2_1']['std_5s']),
        ("Kling v2.1 Standard 10s", PRICING['kling_v2_1']['std_10s']),
        ("Kling v2.1 Pro 5s", PRICING['kling_v2_1']['pro_5s']),
        ("Kling v2.1 Pro 10s", PRICING['kling_v2_1']['pro_10s']),
        ("Kling v2.5 Turbo Standard 5s", PRICING['kling_v2_5_turbo']['std_5s']),
        ("Kling v2.5 Turbo Standard 10s", PRICING['kling_v2_5_turbo']['std_10s']),
        ("Kling v2.5 Turbo Pro 5s", PRICING['kling_v2_5_turbo']['pro_5s']),
        ("Kling v2.5 Turbo Pro 10s", PRICING['kling_v2_5_turbo']['pro_10s']),
        ("Kling v2 Master 5s", PRICING['kling_v2_master']['5s']),
        ("Kling v2 Master 10s", PRICING['kling_v2_master']['10s']),
    ]
    
    for name, cost in scenarios:
        tests = calculate_tests(TOTAL_CREDITS, cost)
        print(f"\n{name}:")
        print(f"  Costo: {format_cost(cost)}")
        print(f"  Pruebas disponibles: {tests}")
    
    print("\n" + "=" * 80)
    print("🖼️  IMÁGENES")
    print("=" * 80)
    
    image_scenarios = [
        ("Gemini Image", PRICING['gemini_image']['image']),
        ("Higgsfield Soul Standard", PRICING['higgsfield_soul_standard']['image']),
        ("Reve Text-to-Image", PRICING['reve_text_to_image']['image']),
    ]
    
    for name, cost in image_scenarios:
        tests = calculate_tests(TOTAL_CREDITS, cost)
        print(f"\n{name}:")
        print(f"  Costo: {format_cost(cost)}")
        print(f"  Pruebas disponibles: {tests}")
    
    print("\n" + "=" * 80)
    print("🎤 AUDIO (ElevenLabs)")
    print("=" * 80)
    
    # Ejemplos de textos comunes
    audio_examples = [
        ("Texto corto (~50 caracteres)", 50),
        ("Texto medio (~100 caracteres)", 100),
        ("Texto largo (~200 caracteres)", 200),
        ("Texto muy largo (~500 caracteres)", 500),
    ]
    
    for name, chars in audio_examples:
        cost = float(PRICING['elevenlabs']['per_character'] * chars)
        tests = calculate_tests(TOTAL_CREDITS, cost)
        print(f"\n{name}:")
        print(f"  Costo: {format_cost(cost)}")
        print(f"  Pruebas disponibles: {tests}")
    
    print("\n" + "=" * 80)
    print("📊 ESCENARIOS COMBINADOS (Ejemplos reales)")
    print("=" * 80)
    
    combined_scenarios = [
        {
            'name': 'Escenario 1: Mix básico',
            'items': [
                ('10 videos HeyGen Avatar v2 (8s)', PRICING['heygen_avatar_v2']['video'] * 8 * 10),
                ('20 imágenes Gemini', PRICING['gemini_image']['image'] * 20),
                ('5 audios (~100 chars)', float(PRICING['elevenlabs']['per_character'] * 100 * 5)),
            ]
        },
        {
            'name': 'Escenario 2: Videos premium',
            'items': [
                ('5 videos Gemini Veo con audio (10s)', PRICING['gemini_veo']['video_audio'] * 10 * 5),
                ('10 videos Sora 2 (8s)', PRICING['sora']['sora-2'] * 8 * 10),
            ]
        },
        {
            'name': 'Escenario 3: Muchas pruebas básicas',
            'items': [
                ('50 videos HeyGen Avatar v2 (8s)', PRICING['heygen_avatar_v2']['video'] * 8 * 50),
                ('100 imágenes', PRICING['gemini_image']['image'] * 100),
            ]
        },
        {
            'name': 'Escenario 4: Mix equilibrado',
            'items': [
                ('20 videos Sora 2 (8s)', PRICING['sora']['sora-2'] * 8 * 20),
                ('30 imágenes', PRICING['gemini_image']['image'] * 30),
                ('10 audios (~150 chars)', float(PRICING['elevenlabs']['per_character'] * 150 * 10)),
            ]
        },
    ]
    
    for scenario in combined_scenarios:
        print(f"\n{scenario['name']}:")
        total_cost = 0
        for item_name, item_cost in scenario['items']:
            total_cost += item_cost
            print(f"  - {item_name}: {format_cost(item_cost)}")
        print(f"  Total: {format_cost(total_cost)}")
        remaining = TOTAL_CREDITS - total_cost
        if remaining >= 0:
            print(f"  Créditos restantes: {format_cost(remaining)}")
        else:
            print(f"  ⚠️  Excede presupuesto por: {format_cost(abs(remaining))}")
    
    print("\n" + "=" * 80)
    print("💡 RECOMENDACIONES")
    print("=" * 80)
    print("""
Para pruebas, se recomienda:

1. **Videos económicos para pruebas frecuentes:**
   - HeyGen Avatar v2: ~40 créditos (8s) = 250 pruebas
   - Sora 2: ~80 créditos (8s) = 125 pruebas
   - Vuela AI Basic: ~24 créditos (8s) = 416 pruebas

2. **Videos premium para demostraciones:**
   - Gemini Veo con audio: ~600 créditos (8s) = 16 pruebas
   - Kling v2 Master: 140-280 créditos = 35-71 pruebas
   - Higgsfield Seedance v1 Pro: 74 créditos = 135 pruebas
   - Kling v2.5 Turbo Pro 10s: 70 créditos = 142 pruebas

3. **Imágenes para previews:**
   - Gemini Image: 2 créditos = 5,000 pruebas
   - Reve: 1 crédito = 10,000 pruebas
   - Higgsfield Soul: 2 créditos = 5,000 pruebas

4. **Mix recomendado para 100€:**
   - 50-100 videos básicos (HeyGen/Sora 2)
   - 200-500 imágenes
   - 50-100 audios cortos
   - Total: ~8,000-9,000 créditos (deja margen)
    """)


if __name__ == '__main__':
    main()

