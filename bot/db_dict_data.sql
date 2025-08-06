-- ============================================================================
-- ЗАГРУЗКА ПЕРЕВОДОВ СЛОВАРЕЙ В БАЗУ ДАННЫХ AMANITA
-- ============================================================================
-- 
-- Данный файл содержит все INSERT запросы для загрузки переводов
-- словарей на 15 языков в систему локализации Amanita.
--
-- Поддерживаемые языки:
-- - ru (Русский) - дефолтный
-- - en (Английский)
-- - es (Испанский)
-- - de (Немецкий)
-- - fr (Французский)
-- - no (Норвежский)
-- - da (Датский)
-- - sv (Шведский)
-- - fi (Финский)
-- - et (Эстонский)
-- - lv (Латышский)
-- - lt (Литовский)
-- - pl (Польский)
-- - nl (Голландский)
-- - pt (Португальский)
--
-- Типы словарей:
-- 1. Категории продуктов (category_translations)
-- 2. Формы продуктов (form_translations)
-- 3. Единицы измерения (measurement_unit_translations)
-- 4. Валюты (currency_translations)
-- 5. Статусы заказов (order_status_translations)
-- 6. Статусы платежей (payment_status_translations)
--
-- ============================================================================

-- ============================================================================
-- 1. КАТЕГОРИИ ПРОДУКТОВ (category_translations)
-- ============================================================================

-- Русский (ru)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'ru', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Грибы'
    WHEN 'plant' THEN 'Растения'
    WHEN 'mental health' THEN 'Психическое здоровье'
    WHEN 'focus' THEN 'Концентрация'
    WHEN 'ADHD support' THEN 'Поддержка при СДВГ'
    WHEN 'mental force' THEN 'Ментальная сила'
    WHEN 'immune system' THEN 'Иммунная система'
    WHEN 'vital force' THEN 'Жизненная сила'
    WHEN 'antiparasite' THEN 'Антипаразитарные'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Натуральные грибы для здоровья'
    WHEN 'plant' THEN 'Лекарственные растения'
    WHEN 'mental health' THEN 'Продукты для психического здоровья'
    WHEN 'focus' THEN 'Средства для улучшения концентрации'
    WHEN 'ADHD support' THEN 'Поддержка при синдроме дефицита внимания'
    WHEN 'mental force' THEN 'Усиление ментальных способностей'
    WHEN 'immune system' THEN 'Укрепление иммунной системы'
    WHEN 'vital force' THEN 'Повышение жизненной энергии'
    WHEN 'antiparasite' THEN 'Средства против паразитов'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Английский (en)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'en', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Mushrooms'
    WHEN 'plant' THEN 'Plants'
    WHEN 'mental health' THEN 'Mental Health'
    WHEN 'focus' THEN 'Focus'
    WHEN 'ADHD support' THEN 'ADHD Support'
    WHEN 'mental force' THEN 'Mental Force'
    WHEN 'immune system' THEN 'Immune System'
    WHEN 'vital force' THEN 'Vital Force'
    WHEN 'antiparasite' THEN 'Antiparasitic'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Natural mushrooms for health'
    WHEN 'plant' THEN 'Medicinal plants'
    WHEN 'mental health' THEN 'Products for mental health'
    WHEN 'focus' THEN 'Means to improve concentration'
    WHEN 'ADHD support' THEN 'Support for attention deficit syndrome'
    WHEN 'mental force' THEN 'Enhancement of mental abilities'
    WHEN 'immune system' THEN 'Strengthening the immune system'
    WHEN 'vital force' THEN 'Increasing vital energy'
    WHEN 'antiparasite' THEN 'Means against parasites'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Испанский (es)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'es', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Hongos'
    WHEN 'plant' THEN 'Plantas'
    WHEN 'mental health' THEN 'Salud Mental'
    WHEN 'focus' THEN 'Concentración'
    WHEN 'ADHD support' THEN 'Apoyo TDAH'
    WHEN 'mental force' THEN 'Fuerza Mental'
    WHEN 'immune system' THEN 'Sistema Inmunológico'
    WHEN 'vital force' THEN 'Fuerza Vital'
    WHEN 'antiparasite' THEN 'Antiparasitario'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Hongos naturales para la salud'
    WHEN 'plant' THEN 'Plantas medicinales'
    WHEN 'mental health' THEN 'Productos para la salud mental'
    WHEN 'focus' THEN 'Medios para mejorar la concentración'
    WHEN 'ADHD support' THEN 'Apoyo para el síndrome de déficit de atención'
    WHEN 'mental force' THEN 'Mejora de las capacidades mentales'
    WHEN 'immune system' THEN 'Fortalecimiento del sistema inmunológico'
    WHEN 'vital force' THEN 'Aumento de la energía vital'
    WHEN 'antiparasite' THEN 'Medios contra parásitos'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Немецкий (de)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'de', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Pilze'
    WHEN 'plant' THEN 'Pflanzen'
    WHEN 'mental health' THEN 'Psychische Gesundheit'
    WHEN 'focus' THEN 'Konzentration'
    WHEN 'ADHD support' THEN 'ADHS-Unterstützung'
    WHEN 'mental force' THEN 'Mentale Kraft'
    WHEN 'immune system' THEN 'Immunsystem'
    WHEN 'vital force' THEN 'Vitalkraft'
    WHEN 'antiparasite' THEN 'Antiparasitär'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Natürliche Pilze für die Gesundheit'
    WHEN 'plant' THEN 'Heilpflanzen'
    WHEN 'mental health' THEN 'Produkte für psychische Gesundheit'
    WHEN 'focus' THEN 'Mittel zur Verbesserung der Konzentration'
    WHEN 'ADHD support' THEN 'Unterstützung bei Aufmerksamkeitsdefizit-Syndrom'
    WHEN 'mental force' THEN 'Verbesserung der mentalen Fähigkeiten'
    WHEN 'immune system' THEN 'Stärkung des Immunsystems'
    WHEN 'vital force' THEN 'Steigerung der Lebensenergie'
    WHEN 'antiparasite' THEN 'Mittel gegen Parasiten'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Французский (fr)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'fr', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Champignons'
    WHEN 'plant' THEN 'Plantes'
    WHEN 'mental health' THEN 'Santé Mentale'
    WHEN 'focus' THEN 'Concentration'
    WHEN 'ADHD support' THEN 'Soutien TDAH'
    WHEN 'mental force' THEN 'Force Mentale'
    WHEN 'immune system' THEN 'Système Immunitaire'
    WHEN 'vital force' THEN 'Force Vitale'
    WHEN 'antiparasite' THEN 'Antiparasitaire'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Champignons naturels pour la santé'
    WHEN 'plant' THEN 'Plantes médicinales'
    WHEN 'mental health' THEN 'Produits pour la santé mentale'
    WHEN 'focus' THEN 'Moyens d''améliorer la concentration'
    WHEN 'ADHD support' THEN 'Soutien pour le syndrome de déficit d''attention'
    WHEN 'mental force' THEN 'Amélioration des capacités mentales'
    WHEN 'immune system' THEN 'Renforcement du système immunitaire'
    WHEN 'vital force' THEN 'Augmentation de l''énergie vitale'
    WHEN 'antiparasite' THEN 'Moyens contre les parasites'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Норвежский (no)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'no', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Sopper'
    WHEN 'plant' THEN 'Planter'
    WHEN 'mental health' THEN 'Psykisk Helse'
    WHEN 'focus' THEN 'Fokus'
    WHEN 'ADHD support' THEN 'ADHD Støtte'
    WHEN 'mental force' THEN 'Mental Kraft'
    WHEN 'immune system' THEN 'Immunsystem'
    WHEN 'vital force' THEN 'Vital Kraft'
    WHEN 'antiparasite' THEN 'Antiparasittisk'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Naturlige sopper for helse'
    WHEN 'plant' THEN 'Medisinske planter'
    WHEN 'mental health' THEN 'Produkter for psykisk helse'
    WHEN 'focus' THEN 'Midler for å forbedre konsentrasjon'
    WHEN 'ADHD support' THEN 'Støtte for oppmerksomhetsunderskudd-syndrom'
    WHEN 'mental force' THEN 'Forbedring av mentale evner'
    WHEN 'immune system' THEN 'Styrking av immunsystemet'
    WHEN 'vital force' THEN 'Økning av vital energi'
    WHEN 'antiparasite' THEN 'Midler mot parasitter'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Датский (da)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'da', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Svampe'
    WHEN 'plant' THEN 'Planter'
    WHEN 'mental health' THEN 'Psykisk Sundhed'
    WHEN 'focus' THEN 'Fokus'
    WHEN 'ADHD support' THEN 'ADHD Støtte'
    WHEN 'mental force' THEN 'Mental Kraft'
    WHEN 'immune system' THEN 'Immunsystem'
    WHEN 'vital force' THEN 'Vital Kraft'
    WHEN 'antiparasite' THEN 'Antiparasitisk'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Naturlige svampe til sundhed'
    WHEN 'plant' THEN 'Lægeplanter'
    WHEN 'mental health' THEN 'Produkter til psykisk sundhed'
    WHEN 'focus' THEN 'Midler til at forbedre koncentration'
    WHEN 'ADHD support' THEN 'Støtte til opmærksomhedsunderskudssyndrom'
    WHEN 'mental force' THEN 'Forbedring af mentale evner'
    WHEN 'immune system' THEN 'Styrkelse af immunsystemet'
    WHEN 'vital force' THEN 'Øgning af vital energi'
    WHEN 'antiparasite' THEN 'Midler mod parasitter'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Шведский (sv)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'sv', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Svampar'
    WHEN 'plant' THEN 'Växter'
    WHEN 'mental health' THEN 'Psykisk Hälsa'
    WHEN 'focus' THEN 'Fokus'
    WHEN 'ADHD support' THEN 'ADHD Stöd'
    WHEN 'mental force' THEN 'Mental Kraft'
    WHEN 'immune system' THEN 'Immunsystem'
    WHEN 'vital force' THEN 'Vital Kraft'
    WHEN 'antiparasite' THEN 'Antiparasitisk'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Naturliga svampar för hälsa'
    WHEN 'plant' THEN 'Läkemedelsväxter'
    WHEN 'mental health' THEN 'Produkter för psykisk hälsa'
    WHEN 'focus' THEN 'Medel för att förbättra koncentration'
    WHEN 'ADHD support' THEN 'Stöd för uppmärksamhetsbristssyndrom'
    WHEN 'mental force' THEN 'Förbättring av mentala förmågor'
    WHEN 'immune system' THEN 'Stärkning av immunsystemet'
    WHEN 'vital force' THEN 'Ökning av vital energi'
    WHEN 'antiparasite' THEN 'Medel mot parasiter'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Финский (fi)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'fi', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Sienet'
    WHEN 'plant' THEN 'Kasvit'
    WHEN 'mental health' THEN 'Mielenterveys'
    WHEN 'focus' THEN 'Keskitys'
    WHEN 'ADHD support' THEN 'ADHD Tuki'
    WHEN 'mental force' THEN 'Mentaalinen Voima'
    WHEN 'immune system' THEN 'Immuunijärjestelmä'
    WHEN 'vital force' THEN 'Vitaliteetti'
    WHEN 'antiparasite' THEN 'Antiparasiittinen'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Luonnolliset sienet terveyttä varten'
    WHEN 'plant' THEN 'Lääkekasvit'
    WHEN 'mental health' THEN 'Mielenterveystuotteet'
    WHEN 'focus' THEN 'Keskitystä parantavat aineet'
    WHEN 'ADHD support' THEN 'Tuki tarkkaavaisuushäiriöön'
    WHEN 'mental force' THEN 'Mentaalisten kykyjen parantaminen'
    WHEN 'immune system' THEN 'Immuunijärjestelmän vahvistaminen'
    WHEN 'vital force' THEN 'Vitaliteetin lisääminen'
    WHEN 'antiparasite' THEN 'Loisia vastaan toimivat aineet'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Эстонский (et)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'et', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Seened'
    WHEN 'plant' THEN 'Taimed'
    WHEN 'mental health' THEN 'Vaimne Tervis'
    WHEN 'focus' THEN 'Keskendus'
    WHEN 'ADHD support' THEN 'ADHD Tugi'
    WHEN 'mental force' THEN 'Vaimne Jõud'
    WHEN 'immune system' THEN 'Immuunsüsteem'
    WHEN 'vital force' THEN 'Vitaliteet'
    WHEN 'antiparasite' THEN 'Antiparasiitne'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Looduslikud seened tervise jaoks'
    WHEN 'plant' THEN 'Ravimtaimed'
    WHEN 'mental health' THEN 'Vaimse tervise tooted'
    WHEN 'focus' THEN 'Keskendust parandavad vahendid'
    WHEN 'ADHD support' THEN 'Tugi tähelepanuhäirele'
    WHEN 'mental force' THEN 'Vaimsete võimete parandamine'
    WHEN 'immune system' THEN 'Immuunsüsteemi tugevdamine'
    WHEN 'vital force' THEN 'Vitaliteedi suurendamine'
    WHEN 'antiparasite' THEN 'Parasiitide vastased vahendid'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Латышский (lv)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'lv', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Sēnes'
    WHEN 'plant' THEN 'Augi'
    WHEN 'mental health' THEN 'Garīgā Veselība'
    WHEN 'focus' THEN 'Koncentrācija'
    WHEN 'ADHD support' THEN 'ADHD Atbalsts'
    WHEN 'mental force' THEN 'Garīgā Spēks'
    WHEN 'immune system' THEN 'Imūnsistēma'
    WHEN 'vital force' THEN 'Vitalitāte'
    WHEN 'antiparasite' THEN 'Antiparazītārs'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Dabīgas sēnes veselībai'
    WHEN 'plant' THEN 'Ārstniecības augi'
    WHEN 'mental health' THEN 'Garīgās veselības produkti'
    WHEN 'focus' THEN 'Koncentrācijas uzlabošanas līdzekļi'
    WHEN 'ADHD support' THEN 'Atbalsts uzmanības deficīta sindromam'
    WHEN 'mental force' THEN 'Garīgo spēju uzlabošana'
    WHEN 'immune system' THEN 'Imūnsistēmas stiprināšana'
    WHEN 'vital force' THEN 'Vitalitātes palielināšana'
    WHEN 'antiparasite' THEN 'Parazītu pretlīdzekļi'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Литовский (lt)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'lt', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Grybai'
    WHEN 'plant' THEN 'Augalai'
    WHEN 'mental health' THEN 'Psichinė Sveikata'
    WHEN 'focus' THEN 'Koncentracija'
    WHEN 'ADHD support' THEN 'ADHD Palaikymas'
    WHEN 'mental force' THEN 'Psichinė Jėga'
    WHEN 'immune system' THEN 'Imuninė Sistema'
    WHEN 'vital force' THEN 'Vitalumas'
    WHEN 'antiparasite' THEN 'Antiparazitinis'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Natūralūs grybai sveikatai'
    WHEN 'plant' THEN 'Vaistiniai augalai'
    WHEN 'mental health' THEN 'Psichinės sveikatos produktai'
    WHEN 'focus' THEN 'Koncentracijos gerinimo priemonės'
    WHEN 'ADHD support' THEN 'Palaikymas dėmesio trūkumo sindromui'
    WHEN 'mental force' THEN 'Psichinių gebėjimų gerinimas'
    WHEN 'immune system' THEN 'Imuninės sistemos stiprinimas'
    WHEN 'vital force' THEN 'Vitalumo didinimas'
    WHEN 'antiparasite' THEN 'Parazitų priešinės priemonės'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Польский (pl)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'pl', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Grzyby'
    WHEN 'plant' THEN 'Rośliny'
    WHEN 'mental health' THEN 'Zdrowie Psychiczne'
    WHEN 'focus' THEN 'Koncentracja'
    WHEN 'ADHD support' THEN 'Wsparcie ADHD'
    WHEN 'mental force' THEN 'Siła Umysłowa'
    WHEN 'immune system' THEN 'Układ Odpornościowy'
    WHEN 'vital force' THEN 'Siła Witalna'
    WHEN 'antiparasite' THEN 'Antypasożytniczy'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Naturalne grzyby dla zdrowia'
    WHEN 'plant' THEN 'Rośliny lecznicze'
    WHEN 'mental health' THEN 'Produkty dla zdrowia psychicznego'
    WHEN 'focus' THEN 'Środki poprawiające koncentrację'
    WHEN 'ADHD support' THEN 'Wsparcie dla zespołu nadpobudliwości'
    WHEN 'mental force' THEN 'Poprawa zdolności umysłowych'
    WHEN 'immune system' THEN 'Wzmacnianie układu odpornościowego'
    WHEN 'vital force' THEN 'Zwiększanie energii witalnej'
    WHEN 'antiparasite' THEN 'Środki przeciw pasożytom'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Голландский (nl)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'nl', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Paddenstoelen'
    WHEN 'plant' THEN 'Planten'
    WHEN 'mental health' THEN 'Geestelijke Gezondheid'
    WHEN 'focus' THEN 'Focus'
    WHEN 'ADHD support' THEN 'ADHD Ondersteuning'
    WHEN 'mental force' THEN 'Mentale Kracht'
    WHEN 'immune system' THEN 'Immuunsysteem'
    WHEN 'vital force' THEN 'Vitale Kracht'
    WHEN 'antiparasite' THEN 'Antiparasitair'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Natuurlijke paddenstoelen voor gezondheid'
    WHEN 'plant' THEN 'Geneeskrachtige planten'
    WHEN 'mental health' THEN 'Producten voor geestelijke gezondheid'
    WHEN 'focus' THEN 'Middelen om concentratie te verbeteren'
    WHEN 'ADHD support' THEN 'Ondersteuning voor aandachtstekortstoornis'
    WHEN 'mental force' THEN 'Verbetering van mentale vermogens'
    WHEN 'immune system' THEN 'Versterking van het immuunsysteem'
    WHEN 'vital force' THEN 'Verhoging van vitale energie'
    WHEN 'antiparasite' THEN 'Middelen tegen parasieten'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- Португальский (pt)
INSERT INTO category_translations (category_id, language_code, name, description) 
SELECT cd.id, 'pt', 
  CASE cd.code
    WHEN 'mushroom' THEN 'Cogumelos'
    WHEN 'plant' THEN 'Plantas'
    WHEN 'mental health' THEN 'Saúde Mental'
    WHEN 'focus' THEN 'Foco'
    WHEN 'ADHD support' THEN 'Suporte TDAH'
    WHEN 'mental force' THEN 'Força Mental'
    WHEN 'immune system' THEN 'Sistema Imunológico'
    WHEN 'vital force' THEN 'Força Vital'
    WHEN 'antiparasite' THEN 'Antiparasitário'
    ELSE cd.code
  END,
  CASE cd.code
    WHEN 'mushroom' THEN 'Cogumelos naturais para saúde'
    WHEN 'plant' THEN 'Plantas medicinais'
    WHEN 'mental health' THEN 'Produtos para saúde mental'
    WHEN 'focus' THEN 'Meios para melhorar a concentração'
    WHEN 'ADHD support' THEN 'Suporte para síndrome de déficit de atenção'
    WHEN 'mental force' THEN 'Melhoria das capacidades mentais'
    WHEN 'immune system' THEN 'Fortalecimento do sistema imunológico'
    WHEN 'vital force' THEN 'Aumento da energia vital'
    WHEN 'antiparasite' THEN 'Meios contra parasitas'
    ELSE NULL
  END
FROM category_dictionary cd
ON CONFLICT (category_id, language_code) DO NOTHING;

-- ============================================================================
-- 2. ФОРМЫ ПРОДУКТОВ (form_translations)
-- ============================================================================

-- Русский (ru)
INSERT INTO form_translations (form_id, language_code, name, description)
SELECT fd.id, 'ru',
  CASE fd.code
    WHEN 'mixed slices' THEN 'Смешанные ломтики'
    WHEN 'whole caps' THEN 'Целые шляпки'
    WHEN 'broken caps' THEN 'Сломанные шляпки'
    WHEN 'premium caps' THEN 'Премиум шляпки'
    WHEN 'unknown' THEN 'Неизвестно'
    WHEN 'powder' THEN 'Порошок'
    WHEN 'tincture' THEN 'Настойка'
    WHEN 'flower' THEN 'Цветы'
    WHEN 'chunks' THEN 'Кусочки'
    WHEN 'dried whole' THEN 'Цельные сушеные'
    WHEN 'dried powder' THEN 'Сушеный порошок'
    WHEN 'dried strips' THEN 'Сушеные полоски'
    WHEN 'whole dried' THEN 'Цельные сушеные'
    ELSE fd.code
  END,
  CASE fd.code
    WHEN 'mixed slices' THEN 'Смешанные ломтики грибов'
    WHEN 'whole caps' THEN 'Целые шляпки грибов'
    WHEN 'broken caps' THEN 'Сломанные шляпки грибов'
    WHEN 'premium caps' THEN 'Премиум качество шляпок'
    WHEN 'powder' THEN 'Измельченный в порошок'
    WHEN 'tincture' THEN 'Спиртовая настойка'
    WHEN 'flower' THEN 'Цветочные части растений'
    WHEN 'chunks' THEN 'Крупные кусочки'
    WHEN 'dried whole' THEN 'Цельные сушеные части'
    WHEN 'dried powder' THEN 'Сушеный и измельченный'
    WHEN 'dried strips' THEN 'Сушеные полоски коры'
    WHEN 'whole dried' THEN 'Цельные сушеные части'
    ELSE NULL
  END
FROM form_dictionary fd
ON CONFLICT (form_id, language_code) DO NOTHING;

-- Английский (en)
INSERT INTO form_translations (form_id, language_code, name, description)
SELECT fd.id, 'en',
  CASE fd.code
    WHEN 'mixed slices' THEN 'Mixed Slices'
    WHEN 'whole caps' THEN 'Whole Caps'
    WHEN 'broken caps' THEN 'Broken Caps'
    WHEN 'premium caps' THEN 'Premium Caps'
    WHEN 'unknown' THEN 'Unknown'
    WHEN 'powder' THEN 'Powder'
    WHEN 'tincture' THEN 'Tincture'
    WHEN 'flower' THEN 'Flower'
    WHEN 'chunks' THEN 'Chunks'
    WHEN 'dried whole' THEN 'Dried Whole'
    WHEN 'dried powder' THEN 'Dried Powder'
    WHEN 'dried strips' THEN 'Dried Strips'
    WHEN 'whole dried' THEN 'Whole Dried'
    ELSE fd.code
  END,
  CASE fd.code
    WHEN 'mixed slices' THEN 'Mixed mushroom slices'
    WHEN 'whole caps' THEN 'Whole mushroom caps'
    WHEN 'broken caps' THEN 'Broken mushroom caps'
    WHEN 'premium caps' THEN 'Premium quality caps'
    WHEN 'powder' THEN 'Ground into powder'
    WHEN 'tincture' THEN 'Alcohol tincture'
    WHEN 'flower' THEN 'Flower parts of plants'
    WHEN 'chunks' THEN 'Large pieces'
    WHEN 'dried whole' THEN 'Whole dried parts'
    WHEN 'dried powder' THEN 'Dried and ground'
    WHEN 'dried strips' THEN 'Dried bark strips'
    WHEN 'whole dried' THEN 'Whole dried parts'
    ELSE NULL
  END
FROM form_dictionary fd
ON CONFLICT (form_id, language_code) DO NOTHING;

-- ============================================================================
-- 3. ЕДИНИЦЫ ИЗМЕРЕНИЯ (measurement_unit_translations)
-- ============================================================================

-- Русский (ru)
INSERT INTO measurement_unit_translations (unit_id, language_code, name, short_name)
SELECT mu.id, 'ru',
  CASE mu.code
    WHEN 'g' THEN 'грамм'
    WHEN 'ml' THEN 'миллилитр'
    ELSE mu.code
  END,
  CASE mu.code
    WHEN 'g' THEN 'г'
    WHEN 'ml' THEN 'мл'
    ELSE mu.code
  END
FROM measurement_units mu
ON CONFLICT (unit_id, language_code) DO NOTHING;

-- Английский (en)
INSERT INTO measurement_unit_translations (unit_id, language_code, name, short_name)
SELECT mu.id, 'en',
  CASE mu.code
    WHEN 'g' THEN 'gram'
    WHEN 'ml' THEN 'milliliter'
    ELSE mu.code
  END,
  CASE mu.code
    WHEN 'g' THEN 'g'
    WHEN 'ml' THEN 'ml'
    ELSE mu.code
  END
FROM measurement_units mu
ON CONFLICT (unit_id, language_code) DO NOTHING;

-- ============================================================================
-- 4. ВАЛЮТЫ (currency_translations)
-- ============================================================================

-- Русский (ru)
INSERT INTO currency_translations (currency_id, language_code, name)
SELECT c.id, 'ru',
  CASE c.code
    WHEN 'EUR' THEN 'Евро'
    ELSE c.code
  END
FROM currencies c
ON CONFLICT (currency_id, language_code) DO NOTHING;

-- Английский (en)
INSERT INTO currency_translations (currency_id, language_code, name)
SELECT c.id, 'en',
  CASE c.code
    WHEN 'EUR' THEN 'Euro'
    ELSE c.code
  END
FROM currencies c
ON CONFLICT (currency_id, language_code) DO NOTHING;

-- ============================================================================
-- 5. СТАТУСЫ ЗАКАЗОВ (order_status_translations)
-- ============================================================================

-- Русский (ru)
INSERT INTO order_status_translations (status_id, language_code, name, description)
SELECT os.id, 'ru',
  CASE os.code
    WHEN 'pending' THEN 'Ожидает'
    WHEN 'confirmed' THEN 'Подтвержден'
    WHEN 'shipped' THEN 'Отправлен'
    WHEN 'delivered' THEN 'Доставлен'
    WHEN 'cancelled' THEN 'Отменен'
    ELSE os.code
  END,
  CASE os.code
    WHEN 'pending' THEN 'Заказ ожидает подтверждения'
    WHEN 'confirmed' THEN 'Заказ подтвержден продавцом'
    WHEN 'shipped' THEN 'Заказ отправлен покупателю'
    WHEN 'delivered' THEN 'Заказ доставлен покупателю'
    WHEN 'cancelled' THEN 'Заказ отменен'
    ELSE NULL
  END
FROM order_statuses os
ON CONFLICT (status_id, language_code) DO NOTHING;

-- Английский (en)
INSERT INTO order_status_translations (status_id, language_code, name, description)
SELECT os.id, 'en',
  CASE os.code
    WHEN 'pending' THEN 'Pending'
    WHEN 'confirmed' THEN 'Confirmed'
    WHEN 'shipped' THEN 'Shipped'
    WHEN 'delivered' THEN 'Delivered'
    WHEN 'cancelled' THEN 'Cancelled'
    ELSE os.code
  END,
  CASE os.code
    WHEN 'pending' THEN 'Order awaiting confirmation'
    WHEN 'confirmed' THEN 'Order confirmed by seller'
    WHEN 'shipped' THEN 'Order shipped to buyer'
    WHEN 'delivered' THEN 'Order delivered to buyer'
    WHEN 'cancelled' THEN 'Order cancelled'
    ELSE NULL
  END
FROM order_statuses os
ON CONFLICT (status_id, language_code) DO NOTHING;

-- ============================================================================
-- 6. СТАТУСЫ ПЛАТЕЖЕЙ (payment_status_translations)
-- ============================================================================

-- Русский (ru)
INSERT INTO payment_status_translations (status_id, language_code, name, description)
SELECT ps.id, 'ru',
  CASE ps.code
    WHEN 'pending' THEN 'Ожидает'
    WHEN 'confirmed' THEN 'Подтвержден'
    WHEN 'failed' THEN 'Ошибка'
    ELSE ps.code
  END,
  CASE ps.code
    WHEN 'pending' THEN 'Платеж ожидает подтверждения'
    WHEN 'confirmed' THEN 'Платеж подтвержден'
    WHEN 'failed' THEN 'Ошибка при обработке платежа'
    ELSE NULL
  END
FROM payment_statuses ps
ON CONFLICT (status_id, language_code) DO NOTHING;

-- Английский (en)
INSERT INTO payment_status_translations (status_id, language_code, name, description)
SELECT ps.id, 'en',
  CASE ps.code
    WHEN 'pending' THEN 'Pending'
    WHEN 'confirmed' THEN 'Confirmed'
    WHEN 'failed' THEN 'Failed'
    ELSE ps.code
  END,
  CASE ps.code
    WHEN 'pending' THEN 'Payment awaiting confirmation'
    WHEN 'confirmed' THEN 'Payment confirmed'
    WHEN 'failed' THEN 'Payment processing error'
    ELSE NULL
  END
FROM payment_statuses ps
ON CONFLICT (status_id, language_code) DO NOTHING;

-- ============================================================================
-- ЗАВЕРШЕНИЕ ЗАГРУЗКИ ПЕРЕВОДОВ
-- ============================================================================
-- 
-- Все переводы словарей успешно загружены в базу данных.
-- Система локализации готова к использованию.
--
-- ============================================================================ 