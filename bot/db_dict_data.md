# Переводы словарей для системы локализации Amanita

## Обзор
Данный файл содержит все переводы словарей для системы локализации Amanita. Переводы организованы по языкам и типам словарей.

## Поддерживаемые языки
- **ru** - Русский (дефолтный)
- **en** - Английский
- **es** - Испанский
- **de** - Немецкий
- **fr** - Французский
- **no** - Норвежский
- **da** - Датский
- **sv** - Шведский
- **fi** - Финский
- **et** - Эстонский
- **lv** - Латышский
- **lt** - Литовский
- **pl** - Польский
- **nl** - Голландский
- **pt** - Португальский

## 1. Категории продуктов (category_translations)

### Русский (ru)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'ru', 
  case cd.code
    when 'mushroom' then 'Грибы'
    when 'plant' then 'Растения'
    when 'mental health' then 'Психическое здоровье'
    when 'focus' then 'Концентрация'
    when 'ADHD support' then 'Поддержка при СДВГ'
    when 'mental force' then 'Ментальная сила'
    when 'immune system' then 'Иммунная система'
    when 'vital force' then 'Жизненная сила'
    when 'antiparasite' then 'Антипаразитарные'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Натуральные грибы для здоровья'
    when 'plant' then 'Лекарственные растения'
    when 'mental health' then 'Продукты для психического здоровья'
    when 'focus' then 'Средства для улучшения концентрации'
    when 'ADHD support' then 'Поддержка при синдроме дефицита внимания'
    when 'mental force' then 'Усиление ментальных способностей'
    when 'immune system' then 'Укрепление иммунной системы'
    when 'vital force' then 'Повышение жизненной энергии'
    when 'antiparasite' then 'Средства против паразитов'
    else null
  end
from category_dictionary cd;
```

### Английский (en)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'en', 
  case cd.code
    when 'mushroom' then 'Mushrooms'
    when 'plant' then 'Plants'
    when 'mental health' then 'Mental Health'
    when 'focus' then 'Focus'
    when 'ADHD support' then 'ADHD Support'
    when 'mental force' then 'Mental Force'
    when 'immune system' then 'Immune System'
    when 'vital force' then 'Vital Force'
    when 'antiparasite' then 'Antiparasitic'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Natural mushrooms for health'
    when 'plant' then 'Medicinal plants'
    when 'mental health' then 'Products for mental health'
    when 'focus' then 'Means to improve concentration'
    when 'ADHD support' then 'Support for attention deficit syndrome'
    when 'mental force' then 'Enhancement of mental abilities'
    when 'immune system' then 'Strengthening the immune system'
    when 'vital force' then 'Increasing vital energy'
    when 'antiparasite' then 'Means against parasites'
    else null
  end
from category_dictionary cd;
```

### Испанский (es)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'es', 
  case cd.code
    when 'mushroom' then 'Hongos'
    when 'plant' then 'Plantas'
    when 'mental health' then 'Salud Mental'
    when 'focus' then 'Concentración'
    when 'ADHD support' then 'Apoyo TDAH'
    when 'mental force' then 'Fuerza Mental'
    when 'immune system' then 'Sistema Inmunológico'
    when 'vital force' then 'Fuerza Vital'
    when 'antiparasite' then 'Antiparasitario'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Hongos naturales para la salud'
    when 'plant' then 'Plantas medicinales'
    when 'mental health' then 'Productos para la salud mental'
    when 'focus' then 'Medios para mejorar la concentración'
    when 'ADHD support' then 'Apoyo para el síndrome de déficit de atención'
    when 'mental force' then 'Mejora de las capacidades mentales'
    when 'immune system' then 'Fortalecimiento del sistema inmunológico'
    when 'vital force' then 'Aumento de la energía vital'
    when 'antiparasite' then 'Medios contra parásitos'
    else null
  end
from category_dictionary cd;
```

### Немецкий (de)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'de', 
  case cd.code
    when 'mushroom' then 'Pilze'
    when 'plant' then 'Pflanzen'
    when 'mental health' then 'Psychische Gesundheit'
    when 'focus' then 'Konzentration'
    when 'ADHD support' then 'ADHS-Unterstützung'
    when 'mental force' then 'Mentale Kraft'
    when 'immune system' then 'Immunsystem'
    when 'vital force' then 'Vitalkraft'
    when 'antiparasite' then 'Antiparasitär'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Natürliche Pilze für die Gesundheit'
    when 'plant' then 'Heilpflanzen'
    when 'mental health' then 'Produkte für psychische Gesundheit'
    when 'focus' then 'Mittel zur Verbesserung der Konzentration'
    when 'ADHD support' then 'Unterstützung bei Aufmerksamkeitsdefizit-Syndrom'
    when 'mental force' then 'Verbesserung der mentalen Fähigkeiten'
    when 'immune system' then 'Stärkung des Immunsystems'
    when 'vital force' then 'Steigerung der Lebensenergie'
    when 'antiparasite' then 'Mittel gegen Parasiten'
    else null
  end
from category_dictionary cd;
```

### Французский (fr)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'fr', 
  case cd.code
    when 'mushroom' then 'Champignons'
    when 'plant' then 'Plantes'
    when 'mental health' then 'Santé Mentale'
    when 'focus' then 'Concentration'
    when 'ADHD support' then 'Soutien TDAH'
    when 'mental force' then 'Force Mentale'
    when 'immune system' then 'Système Immunitaire'
    when 'vital force' then 'Force Vitale'
    when 'antiparasite' then 'Antiparasitaire'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Champignons naturels pour la santé'
    when 'plant' then 'Plantes médicinales'
    when 'mental health' then 'Produits pour la santé mentale'
    when 'focus' then 'Moyens d''améliorer la concentration'
    when 'ADHD support' then 'Soutien pour le syndrome de déficit d''attention'
    when 'mental force' then 'Amélioration des capacités mentales'
    when 'immune system' then 'Renforcement du système immunitaire'
    when 'vital force' then 'Augmentation de l''énergie vitale'
    when 'antiparasite' then 'Moyens contre les parasites'
    else null
  end
from category_dictionary cd;
```

### Норвежский (no)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'no', 
  case cd.code
    when 'mushroom' then 'Sopper'
    when 'plant' then 'Planter'
    when 'mental health' then 'Psykisk Helse'
    when 'focus' then 'Fokus'
    when 'ADHD support' then 'ADHD Støtte'
    when 'mental force' then 'Mental Kraft'
    when 'immune system' then 'Immunsystem'
    when 'vital force' then 'Vital Kraft'
    when 'antiparasite' then 'Antiparasittisk'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Naturlige sopper for helse'
    when 'plant' then 'Medisinske planter'
    when 'mental health' then 'Produkter for psykisk helse'
    when 'focus' then 'Midler for å forbedre konsentrasjon'
    when 'ADHD support' then 'Støtte for oppmerksomhetsunderskudd-syndrom'
    when 'mental force' then 'Forbedring av mentale evner'
    when 'immune system' then 'Styrking av immunsystemet'
    when 'vital force' then 'Økning av vital energi'
    when 'antiparasite' then 'Midler mot parasitter'
    else null
  end
from category_dictionary cd;
```

### Датский (da)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'da', 
  case cd.code
    when 'mushroom' then 'Svampe'
    when 'plant' then 'Planter'
    when 'mental health' then 'Psykisk Sundhed'
    when 'focus' then 'Fokus'
    when 'ADHD support' then 'ADHD Støtte'
    when 'mental force' then 'Mental Kraft'
    when 'immune system' then 'Immunsystem'
    when 'vital force' then 'Vital Kraft'
    when 'antiparasite' then 'Antiparasitisk'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Naturlige svampe til sundhed'
    when 'plant' then 'Lægeplanter'
    when 'mental health' then 'Produkter til psykisk sundhed'
    when 'focus' then 'Midler til at forbedre koncentration'
    when 'ADHD support' then 'Støtte til opmærksomhedsunderskudssyndrom'
    when 'mental force' then 'Forbedring af mentale evner'
    when 'immune system' then 'Styrkelse af immunsystemet'
    when 'vital force' then 'Øgning af vital energi'
    when 'antiparasite' then 'Midler mod parasitter'
    else null
  end
from category_dictionary cd;
```

### Шведский (sv)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'sv', 
  case cd.code
    when 'mushroom' then 'Svampar'
    when 'plant' then 'Växter'
    when 'mental health' then 'Psykisk Hälsa'
    when 'focus' then 'Fokus'
    when 'ADHD support' then 'ADHD Stöd'
    when 'mental force' then 'Mental Kraft'
    when 'immune system' then 'Immunsystem'
    when 'vital force' then 'Vital Kraft'
    when 'antiparasite' then 'Antiparasitisk'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Naturliga svampar för hälsa'
    when 'plant' then 'Läkemedelsväxter'
    when 'mental health' then 'Produkter för psykisk hälsa'
    when 'focus' then 'Medel för att förbättra koncentration'
    when 'ADHD support' then 'Stöd för uppmärksamhetsbristssyndrom'
    when 'mental force' then 'Förbättring av mentala förmågor'
    when 'immune system' then 'Stärkning av immunsystemet'
    when 'vital force' then 'Ökning av vital energi'
    when 'antiparasite' then 'Medel mot parasiter'
    else null
  end
from category_dictionary cd;
```

### Финский (fi)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'fi', 
  case cd.code
    when 'mushroom' then 'Sienet'
    when 'plant' then 'Kasvit'
    when 'mental health' then 'Mielenterveys'
    when 'focus' then 'Keskitys'
    when 'ADHD support' then 'ADHD Tuki'
    when 'mental force' then 'Mentaalinen Voima'
    when 'immune system' then 'Immuunijärjestelmä'
    when 'vital force' then 'Vitaliteetti'
    when 'antiparasite' then 'Antiparasiittinen'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Luonnolliset sienet terveyttä varten'
    when 'plant' then 'Lääkekasvit'
    when 'mental health' then 'Mielenterveystuotteet'
    when 'focus' then 'Keskitystä parantavat aineet'
    when 'ADHD support' then 'Tuki tarkkaavaisuushäiriöön'
    when 'mental force' then 'Mentaalisten kykyjen parantaminen'
    when 'immune system' then 'Immuunijärjestelmän vahvistaminen'
    when 'vital force' then 'Vitaliteetin lisääminen'
    when 'antiparasite' then 'Loisia vastaan toimivat aineet'
    else null
  end
from category_dictionary cd;
```

### Эстонский (et)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'et', 
  case cd.code
    when 'mushroom' then 'Seened'
    when 'plant' then 'Taimed'
    when 'mental health' then 'Vaimne Tervis'
    when 'focus' then 'Keskendus'
    when 'ADHD support' then 'ADHD Tugi'
    when 'mental force' then 'Vaimne Jõud'
    when 'immune system' then 'Immuunsüsteem'
    when 'vital force' then 'Vitaliteet'
    when 'antiparasite' then 'Antiparasiitne'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Looduslikud seened tervise jaoks'
    when 'plant' then 'Ravimtaimed'
    when 'mental health' then 'Vaimse tervise tooted'
    when 'focus' then 'Keskendust parandavad vahendid'
    when 'ADHD support' then 'Tugi tähelepanuhäirele'
    when 'mental force' then 'Vaimsete võimete parandamine'
    when 'immune system' then 'Immuunsüsteemi tugevdamine'
    when 'vital force' then 'Vitaliteedi suurendamine'
    when 'antiparasite' then 'Parasiitide vastased vahendid'
    else null
  end
from category_dictionary cd;
```

### Латышский (lv)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'lv', 
  case cd.code
    when 'mushroom' then 'Sēnes'
    when 'plant' then 'Augi'
    when 'mental health' then 'Garīgā Veselība'
    when 'focus' then 'Koncentrācija'
    when 'ADHD support' then 'ADHD Atbalsts'
    when 'mental force' then 'Garīgā Spēks'
    when 'immune system' then 'Imūnsistēma'
    when 'vital force' then 'Vitalitāte'
    when 'antiparasite' then 'Antiparazītārs'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Dabīgas sēnes veselībai'
    when 'plant' then 'Ārstniecības augi'
    when 'mental health' then 'Garīgās veselības produkti'
    when 'focus' then 'Koncentrācijas uzlabošanas līdzekļi'
    when 'ADHD support' then 'Atbalsts uzmanības deficīta sindromam'
    when 'mental force' then 'Garīgo spēju uzlabošana'
    when 'immune system' then 'Imūnsistēmas stiprināšana'
    when 'vital force' then 'Vitalitātes palielināšana'
    when 'antiparasite' then 'Parazītu pretlīdzekļi'
    else null
  end
from category_dictionary cd;
```

### Литовский (lt)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'lt', 
  case cd.code
    when 'mushroom' then 'Grybai'
    when 'plant' then 'Augalai'
    when 'mental health' then 'Psichinė Sveikata'
    when 'focus' then 'Koncentracija'
    when 'ADHD support' then 'ADHD Palaikymas'
    when 'mental force' then 'Psichinė Jėga'
    when 'immune system' then 'Imuninė Sistema'
    when 'vital force' then 'Vitalumas'
    when 'antiparasite' then 'Antiparazitinis'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Natūralūs grybai sveikatai'
    when 'plant' then 'Vaistiniai augalai'
    when 'mental health' then 'Psichinės sveikatos produktai'
    when 'focus' then 'Koncentracijos gerinimo priemonės'
    when 'ADHD support' then 'Palaikymas dėmesio trūkumo sindromui'
    when 'mental force' then 'Psichinių gebėjimų gerinimas'
    when 'immune system' then 'Imuninės sistemos stiprinimas'
    when 'vital force' then 'Vitalumo didinimas'
    when 'antiparasite' then 'Parazitų priešinės priemonės'
    else null
  end
from category_dictionary cd;
```

### Польский (pl)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'pl', 
  case cd.code
    when 'mushroom' then 'Grzyby'
    when 'plant' then 'Rośliny'
    when 'mental health' then 'Zdrowie Psychiczne'
    when 'focus' then 'Koncentracja'
    when 'ADHD support' then 'Wsparcie ADHD'
    when 'mental force' then 'Siła Umysłowa'
    when 'immune system' then 'Układ Odpornościowy'
    when 'vital force' then 'Siła Witalna'
    when 'antiparasite' then 'Antypasożytniczy'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Naturalne grzyby dla zdrowia'
    when 'plant' then 'Rośliny lecznicze'
    when 'mental health' then 'Produkty dla zdrowia psychicznego'
    when 'focus' then 'Środki poprawiające koncentrację'
    when 'ADHD support' then 'Wsparcie dla zespołu nadpobudliwości'
    when 'mental force' then 'Poprawa zdolności umysłowych'
    when 'immune system' then 'Wzmacnianie układu odpornościowego'
    when 'vital force' then 'Zwiększanie energii witalnej'
    when 'antiparasite' then 'Środki przeciw pasożytom'
    else null
  end
from category_dictionary cd;
```

### Голландский (nl)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'nl', 
  case cd.code
    when 'mushroom' then 'Paddenstoelen'
    when 'plant' then 'Planten'
    when 'mental health' then 'Geestelijke Gezondheid'
    when 'focus' then 'Focus'
    when 'ADHD support' then 'ADHD Ondersteuning'
    when 'mental force' then 'Mentale Kracht'
    when 'immune system' then 'Immuunsysteem'
    when 'vital force' then 'Vitale Kracht'
    when 'antiparasite' then 'Antiparasitair'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Natuurlijke paddenstoelen voor gezondheid'
    when 'plant' then 'Geneeskrachtige planten'
    when 'mental health' then 'Producten voor geestelijke gezondheid'
    when 'focus' then 'Middelen om concentratie te verbeteren'
    when 'ADHD support' then 'Ondersteuning voor aandachtstekortstoornis'
    when 'mental force' then 'Verbetering van mentale vermogens'
    when 'immune system' then 'Versterking van het immuunsysteem'
    when 'vital force' then 'Verhoging van vitale energie'
    when 'antiparasite' then 'Middelen tegen parasieten'
    else null
  end
from category_dictionary cd;
```

### Португальский (pt)
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'pt', 
  case cd.code
    when 'mushroom' then 'Cogumelos'
    when 'plant' then 'Plantas'
    when 'mental health' then 'Saúde Mental'
    when 'focus' then 'Foco'
    when 'ADHD support' then 'Suporte TDAH'
    when 'mental force' then 'Força Mental'
    when 'immune system' then 'Sistema Imunológico'
    when 'vital force' then 'Força Vital'
    when 'antiparasite' then 'Antiparasitário'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Cogumelos naturais para saúde'
    when 'plant' then 'Plantas medicinais'
    when 'mental health' then 'Produtos para saúde mental'
    when 'focus' then 'Meios para melhorar a concentração'
    when 'ADHD support' then 'Suporte para síndrome de déficit de atenção'
    when 'mental force' then 'Melhoria das capacidades mentais'
    when 'immune system' then 'Fortalecimento do sistema imunológico'
    when 'vital force' then 'Aumento da energia vital'
    when 'antiparasite' then 'Meios contra parasitas'
    else null
  end
from category_dictionary cd;
```

## 2. Формы продуктов (form_translations)

### Русский (ru)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'ru',
  case fd.code
    when 'mixed slices' then 'Смешанные ломтики'
    when 'whole caps' then 'Целые шляпки'
    when 'broken caps' then 'Сломанные шляпки'
    when 'premium caps' then 'Премиум шляпки'
    when 'unknown' then 'Неизвестно'
    when 'powder' then 'Порошок'
    when 'tincture' then 'Настойка'
    when 'flower' then 'Цветы'
    when 'chunks' then 'Кусочки'
    when 'dried whole' then 'Цельные сушеные'
    when 'dried powder' then 'Сушеный порошок'
    when 'dried strips' then 'Сушеные полоски'
    when 'whole dried' then 'Цельные сушеные'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Смешанные ломтики грибов'
    when 'whole caps' then 'Целые шляпки грибов'
    when 'broken caps' then 'Сломанные шляпки грибов'
    when 'premium caps' then 'Премиум качество шляпок'
    when 'powder' then 'Измельченный в порошок'
    when 'tincture' then 'Спиртовая настойка'
    when 'flower' then 'Цветочные части растений'
    when 'chunks' then 'Крупные кусочки'
    when 'dried whole' then 'Цельные сушеные части'
    when 'dried powder' then 'Сушеный и измельченный'
    when 'dried strips' then 'Сушеные полоски коры'
    when 'whole dried' then 'Цельные сушеные части'
    else null
  end
from form_dictionary fd;
```

### Английский (en)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'en',
  case fd.code
    when 'mixed slices' then 'Mixed Slices'
    when 'whole caps' then 'Whole Caps'
    when 'broken caps' then 'Broken Caps'
    when 'premium caps' then 'Premium Caps'
    when 'unknown' then 'Unknown'
    when 'powder' then 'Powder'
    when 'tincture' then 'Tincture'
    when 'flower' then 'Flower'
    when 'chunks' then 'Chunks'
    when 'dried whole' then 'Dried Whole'
    when 'dried powder' then 'Dried Powder'
    when 'dried strips' then 'Dried Strips'
    when 'whole dried' then 'Whole Dried'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Mixed mushroom slices'
    when 'whole caps' then 'Whole mushroom caps'
    when 'broken caps' then 'Broken mushroom caps'
    when 'premium caps' then 'Premium quality caps'
    when 'powder' then 'Ground into powder'
    when 'tincture' then 'Alcohol tincture'
    when 'flower' then 'Flower parts of plants'
    when 'chunks' then 'Large pieces'
    when 'dried whole' then 'Whole dried parts'
    when 'dried powder' then 'Dried and ground'
    when 'dried strips' then 'Dried bark strips'
    when 'whole dried' then 'Whole dried parts'
    else null
  end
from form_dictionary fd;
```

### Норвежский (no)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'no',
  case fd.code
    when 'mixed slices' then 'Blandede Skiver'
    when 'whole caps' then 'Hele Hatter'
    when 'broken caps' then 'Ødelagte Hatter'
    when 'premium caps' then 'Premium Hatter'
    when 'unknown' then 'Ukjent'
    when 'powder' then 'Pulver'
    when 'tincture' then 'Tinktur'
    when 'flower' then 'Blomst'
    when 'chunks' then 'Stykker'
    when 'dried whole' then 'Tørket Helt'
    when 'dried powder' then 'Tørket Pulver'
    when 'dried strips' then 'Tørkede Striper'
    when 'whole dried' then 'Helt Tørket'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Blandede soppeskiver'
    when 'whole caps' then 'Hele soppehatter'
    when 'broken caps' then 'Ødelagte soppehatter'
    when 'premium caps' then 'Premium kvalitet hatter'
    when 'powder' then 'Malt til pulver'
    when 'tincture' then 'Alkohol tinktur'
    when 'flower' then 'Blomstedeler av planter'
    when 'chunks' then 'Store stykker'
    when 'dried whole' then 'Hele tørkede deler'
    when 'dried powder' then 'Tørket og malt'
    when 'dried strips' then 'Tørkede barkstriper'
    when 'whole dried' then 'Hele tørkede deler'
    else null
  end
from form_dictionary fd;
```

### Датский (da)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'da',
  case fd.code
    when 'mixed slices' then 'Blandede Skiver'
    when 'whole caps' then 'Hele Hatter'
    when 'broken caps' then 'Ødelagte Hatter'
    when 'premium caps' then 'Premium Hatter'
    when 'unknown' then 'Ukendt'
    when 'powder' then 'Pulver'
    when 'tincture' then 'Tinktur'
    when 'flower' then 'Blomst'
    when 'chunks' then 'Stykker'
    when 'dried whole' then 'Tørret Helt'
    when 'dried powder' then 'Tørret Pulver'
    when 'dried strips' then 'Tørrede Striber'
    when 'whole dried' then 'Helt Tørret'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Blandede svampeskiver'
    when 'whole caps' then 'Hele svampehatter'
    when 'broken caps' then 'Ødelagte svampehatter'
    when 'premium caps' then 'Premium kvalitet hatter'
    when 'powder' then 'Malt til pulver'
    when 'tincture' then 'Alkohol tinktur'
    when 'flower' then 'Blomstedele af planter'
    when 'chunks' then 'Store stykker'
    when 'dried whole' then 'Hele tørrede dele'
    when 'dried powder' then 'Tørret og malt'
    when 'dried strips' then 'Tørrede barkstriber'
    when 'whole dried' then 'Hele tørrede dele'
    else null
  end
from form_dictionary fd;
```

### Шведский (sv)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'sv',
  case fd.code
    when 'mixed slices' then 'Blandade Skivor'
    when 'whole caps' then 'Hela Hattar'
    when 'broken caps' then 'Trasiga Hattar'
    when 'premium caps' then 'Premium Hattar'
    when 'unknown' then 'Okänd'
    when 'powder' then 'Pulver'
    when 'tincture' then 'Tinktur'
    when 'flower' then 'Blomma'
    when 'chunks' then 'Bitarna'
    when 'dried whole' then 'Torkad Helt'
    when 'dried powder' then 'Torkat Pulver'
    when 'dried strips' then 'Torkade Remsar'
    when 'whole dried' then 'Helt Torkad'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Blandade svampskivor'
    when 'whole caps' then 'Hela svamphattar'
    when 'broken caps' then 'Trasiga svamphattar'
    when 'premium caps' then 'Premium kvalitet hattar'
    when 'powder' then 'Malt till pulver'
    when 'tincture' then 'Alkohol tinktur'
    when 'flower' then 'Blomdelar av växter'
    when 'chunks' then 'Stora bitar'
    when 'dried whole' then 'Hela torkade delar'
    when 'dried powder' then 'Torkat och malt'
    when 'dried strips' then 'Torkade barkremsar'
    when 'whole dried' then 'Hela torkade delar'
    else null
  end
from form_dictionary fd;
```

### Финский (fi)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'fi',
  case fd.code
    when 'mixed slices' then 'Sekoitetut Viipaleet'
    when 'whole caps' then 'Kokonaiset Lakit'
    when 'broken caps' then 'Rikkoutuneet Lakit'
    when 'premium caps' then 'Premium Lakit'
    when 'unknown' then 'Tuntematon'
    when 'powder' then 'Jauhe'
    when 'tincture' then 'Tinktuura'
    when 'flower' then 'Kukka'
    when 'chunks' then 'Paloja'
    when 'dried whole' then 'Kuivattu Kokonaan'
    when 'dried powder' then 'Kuivattu Jauhe'
    when 'dried strips' then 'Kuivatut Nauhat'
    when 'whole dried' then 'Kokonaan Kuivattu'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Sekoitetut sieniviipaleet'
    when 'whole caps' then 'Kokonaiset sienilakit'
    when 'broken caps' then 'Rikkoutuneet sienilakit'
    when 'premium caps' then 'Premium laadun lakit'
    when 'powder' then 'Jauhettu jauheeksi'
    when 'tincture' then 'Alkoholi tinktuura'
    when 'flower' then 'Kasvien kukkadet'
    when 'chunks' then 'Suuria paloja'
    when 'dried whole' then 'Kokonaiset kuivatut osat'
    when 'dried powder' then 'Kuivattu ja jauhettu'
    when 'dried strips' then 'Kuivatut kuorenauhat'
    when 'whole dried' then 'Kokonaiset kuivatut osat'
    else null
  end
from form_dictionary fd;
```

### Эстонский (et)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'et',
  case fd.code
    when 'mixed slices' then 'Segatud Viilud'
    when 'whole caps' then 'Terved Kübarad'
    when 'broken caps' then 'Katkised Kübarad'
    when 'premium caps' then 'Premium Kübarad'
    when 'unknown' then 'Tundmatu'
    when 'powder' then 'Pulber'
    when 'tincture' then 'Tinktuur'
    when 'flower' then 'Lill'
    when 'chunks' then 'Tükid'
    when 'dried whole' then 'Kuivatatud Tervikuna'
    when 'dried powder' then 'Kuivatatud Pulber'
    when 'dried strips' then 'Kuivatatud Ribad'
    when 'whole dried' then 'Tervikuna Kuivatatud'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Segatud seeneviilud'
    when 'whole caps' then 'Terved seenekübarad'
    when 'broken caps' then 'Katkised seenekübarad'
    when 'premium caps' then 'Premium kvaliteedi kübarad'
    when 'powder' then 'Jahvatatud pulbriks'
    when 'tincture' then 'Alkoholi tinktuur'
    when 'flower' then 'Taimede õied'
    when 'chunks' then 'Suured tükid'
    when 'dried whole' then 'Terved kuivatatud osad'
    when 'dried powder' then 'Kuivatatud ja jahvatatud'
    when 'dried strips' then 'Kuivatatud koorevööd'
    when 'whole dried' then 'Terved kuivatatud osad'
    else null
  end
from form_dictionary fd;
```

### Латышский (lv)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'lv',
  case fd.code
    when 'mixed slices' then 'Jaukti Šķēles'
    when 'whole caps' then 'Veselas Cepures'
    when 'broken caps' then 'Salauztas Cepures'
    when 'premium caps' then 'Premium Cepures'
    when 'unknown' then 'Nezināms'
    when 'powder' then 'Pulveris'
    when 'tincture' then 'Tinktūra'
    when 'flower' then 'Zieds'
    when 'chunks' then 'Gabali'
    when 'dried whole' then 'Žāvēts Vesels'
    when 'dried powder' then 'Žāvēts Pulveris'
    when 'dried strips' then 'Žāvētas Lentes'
    when 'whole dried' then 'Vesels Žāvēts'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Jaukti sēņu šķēles'
    when 'whole caps' then 'Veselas sēņu cepures'
    when 'broken caps' then 'Salauztas sēņu cepures'
    when 'premium caps' then 'Premium kvalitātes cepures'
    when 'powder' then 'Sasmalcināts pulverī'
    when 'tincture' then 'Spirta tinktūra'
    when 'flower' then 'Augu ziedi'
    when 'chunks' then 'Lieli gabali'
    when 'dried whole' then 'Veselas žāvētas daļas'
    when 'dried powder' then 'Žāvēts un sasmalcināts'
    when 'dried strips' then 'Žāvētas mizas lentes'
    when 'whole dried' then 'Veselas žāvētas daļas'
    else null
  end
from form_dictionary fd;
```

### Литовский (lt)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'lt',
  case fd.code
    when 'mixed slices' then 'Mišrūs Skiltelės'
    when 'whole caps' then 'Visi Kepurėliai'
    when 'broken caps' then 'Sulaužyti Kepurėliai'
    when 'premium caps' then 'Premium Kepurėliai'
    when 'unknown' then 'Nežinomas'
    when 'powder' then 'Milteiai'
    when 'tincture' then 'Tinktūra'
    when 'flower' then 'Gėlė'
    when 'chunks' then 'Gabaliukai'
    when 'dried whole' then 'Džiovinti Visi'
    when 'dried powder' then 'Džiovinti Milteiai'
    when 'dried strips' then 'Džiovintos Juostelės'
    when 'whole dried' then 'Visi Džiovinti'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Mišrūs grybų skiltelės'
    when 'whole caps' then 'Visi grybų kepurėliai'
    when 'broken caps' then 'Sulaužyti grybų kepurėliai'
    when 'premium caps' then 'Premium kokybės kepurėliai'
    when 'powder' then 'Sutrinti į miltelius'
    when 'tincture' then 'Spirito tinktūra'
    when 'flower' then 'Augalų gėlės'
    when 'chunks' then 'Dideli gabaliukai'
    when 'dried whole' then 'Visi džiovinti dalys'
    when 'dried powder' then 'Džiovinti ir sutrinti'
    when 'dried strips' then 'Džiovintos žievės juostelės'
    when 'whole dried' then 'Visi džiovinti dalys'
    else null
  end
from form_dictionary fd;
```

### Польский (pl)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'pl',
  case fd.code
    when 'mixed slices' then 'Mieszane Plastry'
    when 'whole caps' then 'Całe Kapelusze'
    when 'broken caps' then 'Złamane Kapelusze'
    when 'premium caps' then 'Premium Kapelusze'
    when 'unknown' then 'Nieznane'
    when 'powder' then 'Proszek'
    when 'tincture' then 'Nalewka'
    when 'flower' then 'Kwiat'
    when 'chunks' then 'Kawałki'
    when 'dried whole' then 'Suszone Całe'
    when 'dried powder' then 'Suszone Proszek'
    when 'dried strips' then 'Suszone Paski'
    when 'whole dried' then 'Całe Suszone'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Mieszane plastry grzybów'
    when 'whole caps' then 'Całe kapelusze grzybów'
    when 'broken caps' then 'Złamane kapelusze grzybów'
    when 'premium caps' then 'Premium jakość kapeluszy'
    when 'powder' then 'Zmielone na proszek'
    when 'tincture' then 'Nalewka alkoholowa'
    when 'flower' then 'Kwiaty roślin'
    when 'chunks' then 'Duże kawałki'
    when 'dried whole' then 'Całe suszone części'
    when 'dried powder' then 'Suszone i mielone'
    when 'dried strips' then 'Suszone paski kory'
    when 'whole dried' then 'Całe suszone części'
    else null
  end
from form_dictionary fd;
```

### Голландский (nl)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'nl',
  case fd.code
    when 'mixed slices' then 'Gemengde Plakken'
    when 'whole caps' then 'Hele Hoeden'
    when 'broken caps' then 'Gebroken Hoeden'
    when 'premium caps' then 'Premium Hoeden'
    when 'unknown' then 'Onbekend'
    when 'powder' then 'Poeder'
    when 'tincture' then 'Tinctuur'
    when 'flower' then 'Bloem'
    when 'chunks' then 'Stukken'
    when 'dried whole' then 'Gedroogd Geheel'
    when 'dried powder' then 'Gedroogd Poeder'
    when 'dried strips' then 'Gedroogde Stroken'
    when 'whole dried' then 'Geheel Gedroogd'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Gemengde paddenstoelenplakken'
    when 'whole caps' then 'Hele paddenstoelenhoeden'
    when 'broken caps' then 'Gebroken paddenstoelenhoeden'
    when 'premium caps' then 'Premium kwaliteit hoeden'
    when 'powder' then 'Gemalen tot poeder'
    when 'tincture' then 'Alcohol tinctuur'
    when 'flower' then 'Bloemendelen van planten'
    when 'chunks' then 'Grote stukken'
    when 'dried whole' then 'Hele gedroogde delen'
    when 'dried powder' then 'Gedroogd en gemalen'
    when 'dried strips' then 'Gedroogde schorsstroken'
    when 'whole dried' then 'Hele gedroogde delen'
    else null
  end
from form_dictionary fd;
```

### Португальский (pt)
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'pt',
  case fd.code
    when 'mixed slices' then 'Fatias Misturadas'
    when 'whole caps' then 'Chapéus Inteiros'
    when 'broken caps' then 'Chapéus Quebrados'
    when 'premium caps' then 'Chapéus Premium'
    when 'unknown' then 'Desconhecido'
    when 'powder' then 'Pó'
    when 'tincture' then 'Tintura'
    when 'flower' then 'Flor'
    when 'chunks' then 'Pedacinhos'
    when 'dried whole' then 'Seco Inteiro'
    when 'dried powder' then 'Pó Seco'
    when 'dried strips' then 'Tiras Secas'
    when 'whole dried' then 'Inteiro Seco'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Fatias misturadas de cogumelos'
    when 'whole caps' then 'Chapéus inteiros de cogumelos'
    when 'broken caps' then 'Chapéus quebrados de cogumelos'
    when 'premium caps' then 'Chapéus de qualidade premium'
    when 'powder' then 'Moído em pó'
    when 'tincture' then 'Tintura alcoólica'
    when 'flower' then 'Partes florais das plantas'
    when 'chunks' then 'Pedacinhos grandes'
    when 'dried whole' then 'Partes inteiras secas'
    when 'dried powder' then 'Seco e moído'
    when 'dried strips' then 'Tiras de casca secas'
    when 'whole dried' then 'Partes inteiras secas'
    else null
  end
from form_dictionary fd;
```

## 3. Единицы измерения (measurement_unit_translations)

### Русский (ru)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'ru',
  case mu.code
    when 'g' then 'грамм'
    when 'ml' then 'миллилитр'
    else mu.code
  end,
  case mu.code
    when 'g' then 'г'
    when 'ml' then 'мл'
    else mu.code
  end
from measurement_units mu;
```

### Английский (en)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'en',
  case mu.code
    when 'g' then 'gram'
    when 'ml' then 'milliliter'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Испанский (es)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'es',
  case mu.code
    when 'g' then 'gramo'
    when 'ml' then 'mililitro'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Немецкий (de)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'de',
  case mu.code
    when 'g' then 'Gramm'
    when 'ml' then 'Milliliter'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Французский (fr)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'fr',
  case mu.code
    when 'g' then 'gramme'
    when 'ml' then 'millilitre'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Норвежский (no)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'no',
  case mu.code
    when 'g' then 'gram'
    when 'ml' then 'milliliter'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Датский (da)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'da',
  case mu.code
    when 'g' then 'gram'
    when 'ml' then 'milliliter'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Шведский (sv)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'sv',
  case mu.code
    when 'g' then 'gram'
    when 'ml' then 'milliliter'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Финский (fi)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'fi',
  case mu.code
    when 'g' then 'gramma'
    when 'ml' then 'millilitra'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Эстонский (et)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'et',
  case mu.code
    when 'g' then 'gramm'
    when 'ml' then 'milliliiter'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Латышский (lv)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'lv',
  case mu.code
    when 'g' then 'grams'
    when 'ml' then 'mililitrs'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Литовский (lt)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'lt',
  case mu.code
    when 'g' then 'gramas'
    when 'ml' then 'mililitras'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Польский (pl)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'pl',
  case mu.code
    when 'g' then 'gram'
    when 'ml' then 'mililitr'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Голландский (nl)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'nl',
  case mu.code
    when 'g' then 'gram'
    when 'ml' then 'milliliter'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

### Португальский (pt)
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'pt',
  case mu.code
    when 'g' then 'grama'
    when 'ml' then 'mililitro'
    else mu.code
  end,
  case mu.code
    when 'g' then 'g'
    when 'ml' then 'ml'
    else mu.code
  end
from measurement_units mu;
```

## 4. Валюты (currency_translations)

### Русский (ru)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'ru',
  case c.code
    when 'EUR' then 'Евро'
    else c.code
  end
from currencies c;
```

### Английский (en)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'en',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Испанский (es)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'es',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Немецкий (de)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'de',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Французский (fr)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'fr',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Норвежский (no)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'no',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Датский (da)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'da',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Шведский (sv)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'sv',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Финский (fi)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'fi',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Эстонский (et)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'et',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Латышский (lv)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'lv',
  case c.code
    when 'EUR' then 'Eiro'
    else c.code
  end
from currencies c;
```

### Литовский (lt)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'lt',
  case c.code
    when 'EUR' then 'Euras'
    else c.code
  end
from currencies c;
```

### Польский (pl)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'pl',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Голландский (nl)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'nl',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

### Португальский (pt)
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'pt',
  case c.code
    when 'EUR' then 'Euro'
    else c.code
  end
from currencies c;
```

## 5. Статусы заказов (order_status_translations)

### Русский (ru)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'ru',
  case os.code
    when 'pending' then 'Ожидает'
    when 'confirmed' then 'Подтвержден'
    when 'shipped' then 'Отправлен'
    when 'delivered' then 'Доставлен'
    when 'cancelled' then 'Отменен'
    else os.code
  end,
  case os.code
    when 'pending' then 'Заказ ожидает подтверждения'
    when 'confirmed' then 'Заказ подтвержден продавцом'
    when 'shipped' then 'Заказ отправлен покупателю'
    when 'delivered' then 'Заказ доставлен покупателю'
    when 'cancelled' then 'Заказ отменен'
    else null
  end
from order_statuses os;
```

### Английский (en)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'en',
  case os.code
    when 'pending' then 'Pending'
    when 'confirmed' then 'Confirmed'
    when 'shipped' then 'Shipped'
    when 'delivered' then 'Delivered'
    when 'cancelled' then 'Cancelled'
    else os.code
  end,
  case os.code
    when 'pending' then 'Order awaiting confirmation'
    when 'confirmed' then 'Order confirmed by seller'
    when 'shipped' then 'Order shipped to buyer'
    when 'delivered' then 'Order delivered to buyer'
    when 'cancelled' then 'Order cancelled'
    else null
  end
from order_statuses os;
```

### Испанский (es)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'es',
  case os.code
    when 'pending' then 'Pendiente'
    when 'confirmed' then 'Confirmado'
    when 'shipped' then 'Enviado'
    when 'delivered' then 'Entregado'
    when 'cancelled' then 'Cancelado'
    else os.code
  end,
  case os.code
    when 'pending' then 'Pedido esperando confirmación'
    when 'confirmed' then 'Pedido confirmado por el vendedor'
    when 'shipped' then 'Pedido enviado al comprador'
    when 'delivered' then 'Pedido entregado al comprador'
    when 'cancelled' then 'Pedido cancelado'
    else null
  end
from order_statuses os;
```

### Немецкий (de)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'de',
  case os.code
    when 'pending' then 'Ausstehend'
    when 'confirmed' then 'Bestätigt'
    when 'shipped' then 'Versendet'
    when 'delivered' then 'Geliefert'
    when 'cancelled' then 'Storniert'
    else os.code
  end,
  case os.code
    when 'pending' then 'Bestellung wartet auf Bestätigung'
    when 'confirmed' then 'Bestellung vom Verkäufer bestätigt'
    when 'shipped' then 'Bestellung an Käufer versendet'
    when 'delivered' then 'Bestellung an Käufer geliefert'
    when 'cancelled' then 'Bestellung storniert'
    else null
  end
from order_statuses os;
```

### Французский (fr)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'fr',
  case os.code
    when 'pending' then 'En Attente'
    when 'confirmed' then 'Confirmé'
    when 'shipped' then 'Expédié'
    when 'delivered' then 'Livré'
    when 'cancelled' then 'Annulé'
    else os.code
  end,
  case os.code
    when 'pending' then 'Commande en attente de confirmation'
    when 'confirmed' then 'Commande confirmée par le vendeur'
    when 'shipped' then 'Commande expédiée à l''acheteur'
    when 'delivered' then 'Commande livrée à l''acheteur'
    when 'cancelled' then 'Commande annulée'
    else null
  end
from order_statuses os;
```

### Норвежский (no)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'no',
  case os.code
    when 'pending' then 'Venter'
    when 'confirmed' then 'Bekreftet'
    when 'shipped' then 'Sendt'
    when 'delivered' then 'Levert'
    when 'cancelled' then 'Kansellert'
    else os.code
  end,
  case os.code
    when 'pending' then 'Bestilling venter på bekreftelse'
    when 'confirmed' then 'Bestilling bekreftet av selger'
    when 'shipped' then 'Bestilling sendt til kjøper'
    when 'delivered' then 'Bestilling levert til kjøper'
    when 'cancelled' then 'Bestilling kansellert'
    else null
  end
from order_statuses os;
```

### Датский (da)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'da',
  case os.code
    when 'pending' then 'Venter'
    when 'confirmed' then 'Bekræftet'
    when 'shipped' then 'Sendt'
    when 'delivered' then 'Leveret'
    when 'cancelled' then 'Annulleret'
    else os.code
  end,
  case os.code
    when 'pending' then 'Bestilling venter på bekræftelse'
    when 'confirmed' then 'Bestilling bekræftet af sælger'
    when 'shipped' then 'Bestilling sendt til køber'
    when 'delivered' then 'Bestilling leveret til køber'
    when 'cancelled' then 'Bestilling annulleret'
    else null
  end
from order_statuses os;
```

### Шведский (sv)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'sv',
  case os.code
    when 'pending' then 'Väntar'
    when 'confirmed' then 'Bekräftad'
    when 'shipped' then 'Skickad'
    when 'delivered' then 'Levererad'
    when 'cancelled' then 'Avbruten'
    else os.code
  end,
  case os.code
    when 'pending' then 'Beställning väntar på bekräftelse'
    when 'confirmed' then 'Beställning bekräftad av säljare'
    when 'shipped' then 'Beställning skickad till köpare'
    when 'delivered' then 'Beställning levererad till köpare'
    when 'cancelled' then 'Beställning avbruten'
    else null
  end
from order_statuses os;
```

### Финский (fi)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'fi',
  case os.code
    when 'pending' then 'Odottaa'
    when 'confirmed' then 'Vahvistettu'
    when 'shipped' then 'Lähetetty'
    when 'delivered' then 'Toimitettu'
    when 'cancelled' then 'Peruttu'
    else os.code
  end,
  case os.code
    when 'pending' then 'Tilaus odottaa vahvistusta'
    when 'confirmed' then 'Tilaus vahvistettu myyjän toimesta'
    when 'shipped' then 'Tilaus lähetetty ostajalle'
    when 'delivered' then 'Tilaus toimitettu ostajalle'
    when 'cancelled' then 'Tilaus peruttu'
    else null
  end
from order_statuses os;
```

### Эстонский (et)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'et',
  case os.code
    when 'pending' then 'Ootab'
    when 'confirmed' then 'Kinnitatud'
    when 'shipped' then 'Saadetud'
    when 'delivered' then 'Kohale toimetatud'
    when 'cancelled' then 'Tühistatud'
    else os.code
  end,
  case os.code
    when 'pending' then 'Tellimus ootab kinnitamist'
    when 'confirmed' then 'Tellimus kinnitatud müüja poolt'
    when 'shipped' then 'Tellimus saadetud ostjale'
    when 'delivered' then 'Tellimus kohale toimetatud ostjale'
    when 'cancelled' then 'Tellimus tühistatud'
    else null
  end
from order_statuses os;
```

### Латышский (lv)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'lv',
  case os.code
    when 'pending' then 'Gaida'
    when 'confirmed' then 'Apstiprināts'
    when 'shipped' then 'Nosūtīts'
    when 'delivered' then 'Piegādāts'
    when 'cancelled' then 'Atcelts'
    else os.code
  end,
  case os.code
    when 'pending' then 'Pasūtījums gaida apstiprinājumu'
    when 'confirmed' then 'Pasūtījums apstiprināts pārdevēja'
    when 'shipped' then 'Pasūtījums nosūtīts pircējam'
    when 'delivered' then 'Pasūtījums piegādāts pircējam'
    when 'cancelled' then 'Pasūtījums atcelts'
    else null
  end
from order_statuses os;
```

### Литовский (lt)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'lt',
  case os.code
    when 'pending' then 'Laukia'
    when 'confirmed' then 'Patvirtintas'
    when 'shipped' then 'Išsiųstas'
    when 'delivered' then 'Pristatytas'
    when 'cancelled' then 'Atšauktas'
    else os.code
  end,
  case os.code
    when 'pending' then 'Užsakymas laukia patvirtinimo'
    when 'confirmed' then 'Užsakymas patvirtintas pardavėjo'
    when 'shipped' then 'Užsakymas išsiųstas pirkėjui'
    when 'delivered' then 'Užsakymas pristatytas pirkėjui'
    when 'cancelled' then 'Užsakymas atšauktas'
    else null
  end
from order_statuses os;
```

### Польский (pl)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'pl',
  case os.code
    when 'pending' then 'Oczekuje'
    when 'confirmed' then 'Potwierdzone'
    when 'shipped' then 'Wysłane'
    when 'delivered' then 'Dostarczone'
    when 'cancelled' then 'Anulowane'
    else os.code
  end,
  case os.code
    when 'pending' then 'Zamówienie oczekuje na potwierdzenie'
    when 'confirmed' then 'Zamówienie potwierdzone przez sprzedawcę'
    when 'shipped' then 'Zamówienie wysłane do kupującego'
    when 'delivered' then 'Zamówienie dostarczone do kupującego'
    when 'cancelled' then 'Zamówienie anulowane'
    else null
  end
from order_statuses os;
```

### Голландский (nl)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'nl',
  case os.code
    when 'pending' then 'In Afwachting'
    when 'confirmed' then 'Bevestigd'
    when 'shipped' then 'Verzonden'
    when 'delivered' then 'Afgeleverd'
    when 'cancelled' then 'Geannuleerd'
    else os.code
  end,
  case os.code
    when 'pending' then 'Bestelling wacht op bevestiging'
    when 'confirmed' then 'Bestelling bevestigd door verkoper'
    when 'shipped' then 'Bestelling verzonden naar koper'
    when 'delivered' then 'Bestelling afgeleverd aan koper'
    when 'cancelled' then 'Bestelling geannuleerd'
    else null
  end
from order_statuses os;
```

### Португальский (pt)
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'pt',
  case os.code
    when 'pending' then 'Pendente'
    when 'confirmed' then 'Confirmado'
    when 'shipped' then 'Enviado'
    when 'delivered' then 'Entregue'
    when 'cancelled' then 'Cancelado'
    else os.code
  end,
  case os.code
    when 'pending' then 'Pedido aguardando confirmação'
    when 'confirmed' then 'Pedido confirmado pelo vendedor'
    when 'shipped' then 'Pedido enviado ao comprador'
    when 'delivered' then 'Pedido entregue ao comprador'
    when 'cancelled' then 'Pedido cancelado'
    else null
  end
from order_statuses os;
```

## 6. Статусы платежей (payment_status_translations)

### Русский (ru)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'ru',
  case ps.code
    when 'pending' then 'Ожидает'
    when 'confirmed' then 'Подтвержден'
    when 'failed' then 'Ошибка'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Платеж ожидает подтверждения'
    when 'confirmed' then 'Платеж подтвержден'
    when 'failed' then 'Ошибка при обработке платежа'
    else null
  end
from payment_statuses ps;
```

### Английский (en)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'en',
  case ps.code
    when 'pending' then 'Pending'
    when 'confirmed' then 'Confirmed'
    when 'failed' then 'Failed'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Payment awaiting confirmation'
    when 'confirmed' then 'Payment confirmed'
    when 'failed' then 'Payment processing error'
    else null
  end
from payment_statuses ps;
```

### Испанский (es)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'es',
  case ps.code
    when 'pending' then 'Pendiente'
    when 'confirmed' then 'Confirmado'
    when 'failed' then 'Fallido'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Pago esperando confirmación'
    when 'confirmed' then 'Pago confirmado'
    when 'failed' then 'Error en el procesamiento del pago'
    else null
  end
from payment_statuses ps;
```

### Немецкий (de)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'de',
  case ps.code
    when 'pending' then 'Ausstehend'
    when 'confirmed' then 'Bestätigt'
    when 'failed' then 'Fehlgeschlagen'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Zahlung wartet auf Bestätigung'
    when 'confirmed' then 'Zahlung bestätigt'
    when 'failed' then 'Fehler bei der Zahlungsverarbeitung'
    else null
  end
from payment_statuses ps;
```

### Французский (fr)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'fr',
  case ps.code
    when 'pending' then 'En Attente'
    when 'confirmed' then 'Confirmé'
    when 'failed' then 'Échoué'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Paiement en attente de confirmation'
    when 'confirmed' then 'Paiement confirmé'
    when 'failed' then 'Erreur de traitement du paiement'
    else null
  end
from payment_statuses ps;
```

### Норвежский (no)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'no',
  case ps.code
    when 'pending' then 'Venter'
    when 'confirmed' then 'Bekreftet'
    when 'failed' then 'Feilet'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Betaling venter på bekreftelse'
    when 'confirmed' then 'Betaling bekreftet'
    when 'failed' then 'Feil ved behandling av betaling'
    else null
  end
from payment_statuses ps;
```

### Датский (da)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'da',
  case ps.code
    when 'pending' then 'Venter'
    when 'confirmed' then 'Bekræftet'
    when 'failed' then 'Fejlet'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Betaling venter på bekræftelse'
    when 'confirmed' then 'Betaling bekræftet'
    when 'failed' then 'Fejl ved behandling af betaling'
    else null
  end
from payment_statuses ps;
```

### Шведский (sv)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'sv',
  case ps.code
    when 'pending' then 'Väntar'
    when 'confirmed' then 'Bekräftad'
    when 'failed' then 'Misslyckades'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Betalning väntar på bekräftelse'
    when 'confirmed' then 'Betalning bekräftad'
    when 'failed' then 'Fel vid behandling av betalning'
    else null
  end
from payment_statuses ps;
```

### Финский (fi)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'fi',
  case ps.code
    when 'pending' then 'Odottaa'
    when 'confirmed' then 'Vahvistettu'
    when 'failed' then 'Epäonnistui'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Maksu odottaa vahvistusta'
    when 'confirmed' then 'Maksu vahvistettu'
    when 'failed' then 'Virhe maksun käsittelyssä'
    else null
  end
from payment_statuses ps;
```

### Эстонский (et)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'et',
  case ps.code
    when 'pending' then 'Ootab'
    when 'confirmed' then 'Kinnitatud'
    when 'failed' then 'Ebaõnnestus'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Makse ootab kinnitamist'
    when 'confirmed' then 'Makse kinnitatud'
    when 'failed' then 'Viga makse töötlemisel'
    else null
  end
from payment_statuses ps;
```

### Латышский (lv)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'lv',
  case ps.code
    when 'pending' then 'Gaida'
    when 'confirmed' then 'Apstiprināts'
    when 'failed' then 'Neizdevās'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Maksājums gaida apstiprinājumu'
    when 'confirmed' then 'Maksājums apstiprināts'
    when 'failed' then 'Kļūda maksājuma apstrādē'
    else null
  end
from payment_statuses ps;
```

### Литовский (lt)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'lt',
  case ps.code
    when 'pending' then 'Laukia'
    when 'confirmed' then 'Patvirtintas'
    when 'failed' then 'Nepavyko'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Mokėjimas laukia patvirtinimo'
    when 'confirmed' then 'Mokėjimas patvirtintas'
    when 'failed' then 'Klaida mokėjimo apdorojime'
    else null
  end
from payment_statuses ps;
```

### Польский (pl)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'pl',
  case ps.code
    when 'pending' then 'Oczekuje'
    when 'confirmed' then 'Potwierdzone'
    when 'failed' then 'Nieudane'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Płatność oczekuje na potwierdzenie'
    when 'confirmed' then 'Płatność potwierdzona'
    when 'failed' then 'Błąd w przetwarzaniu płatności'
    else null
  end
from payment_statuses ps;
```

### Голландский (nl)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'nl',
  case ps.code
    when 'pending' then 'In Afwachting'
    when 'confirmed' then 'Bevestigd'
    when 'failed' then 'Mislukt'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Betaling wacht op bevestiging'
    when 'confirmed' then 'Betaling bevestigd'
    when 'failed' then 'Fout bij verwerking van betaling'
    else null
  end
from payment_statuses ps;
```

### Португальский (pt)
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'pt',
  case ps.code
    when 'pending' then 'Pendente'
    when 'confirmed' then 'Confirmado'
    when 'failed' then 'Falhou'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Pagamento aguardando confirmação'
    when 'confirmed' then 'Pagamento confirmado'
    when 'failed' then 'Erro no processamento do pagamento'
    else null
  end
from payment_statuses ps;
```

## Примечания

1. **Дефолтный язык**: Русский (ru) является дефолтным языком системы
2. **Fallback**: При отсутствии перевода возвращается исходный код
3. **Автоматическое связывание**: Все переводы автоматически связываются с базовыми записями через CASE выражения
4. **Расширяемость**: Легко добавить новые языки, скопировав структуру и изменив переводы

## Использование

Для добавления переводов в базу данных выполните соответствующие INSERT запросы для нужного языка. Все запросы используют CASE выражения для автоматического связывания с базовыми записями словарей.
