# Mercek — Nihai Veri Şemaları (16.10.2026)

Bu doküman, şema gözden geçirmesinde kullanıcıyla tek tek kesinleşen **nihai tablo yapılarını** içerir. Mevcut kod (`tools/mercek_data/db.py`) ve üretilmiş veri (`data/out/`) henüz **eski** şemadadır; tüm değişiklikler en sonda tek seferde işlenecek (bkz. `HANDOFF.md` §5).

**Genel kurallar**
- Mercek'in türettiği (AI ya da kod) alanlar `mercek_assigned_*` önekiyle adlandırılır.
- "Servis" kavramı her yerde **departman** (`department_id`).
- Firma adı örneklerde **fineart** (`dalan` kullanılmaz). E-posta alan adı `ornek.test`.
- KVKK: gerçek kişi verisi yok; logda IP, makine adı, bağlantı kimliği, AD kullanıcı adı üretilmez. Metin alanlarında kişisel veri olmaz.
- AI önerir, insan onaylar: kurallar, duyurular, talepler, kapsam ekleri.
- Hesaplar (sayılar, eşikler, departman ataması, efor, takvim) kodda; AI açıklar, çıkarır, sınıflandırır.
- `search_text` = AI Search'e indexer ile eşitlenen hesaplanan kolon (SQL change tracking).

Durum: ✅ JSON üretildi (`datav2/`) · 🟡 şema kesin, JSON bekliyor · ⏳ şema gözden geçirilecek

---

## A. Katalog tabloları

### departments ✅ (`departments.json`, 6)
| Kolon | Açıklama | Örnek |
|---|---|---|
| department_id | Departman anahtarı | `KREDI_TAKIP` |
| name | Ad | Kredi Kullandırım Departmanı |
| description | Sorumluluk alanı (parametreleri dahil) | Yeni kredi kullandırım, ödeme planı… |

Değerler: KREDI_KULLANDIRIM, KREDI_TAKIP, KART_YONETIM, FATURA_ODEME (Ödeme ve Talimat), HESAP_YONETIM, MUSTERI_YONETIM. **PARAMETRE_YONETIM yok** (her departman kendi parametresini girer).

### screens ✅ (`screens.json`, 9)
| Kolon | Açıklama | Örnek |
|---|---|---|
| code | Ekran kodu | `ODMTTLMT` |
| name | Ad | Fatura Talimat Bilgileri Giriş |
| module | Modül | `ODM` |
| type | Ekran tipi | `T` |
| description | Kısa açıklama | … |
| components_json | Bileşen listesi | `["abone numarası (6–12 hane)", …]` |
| flow_json | Akış adımları | `["Müşteri seç", …]` |
| files_json | Kod dosyaları (frontend/backend) | `{"frontend": [...], "backend": [...]}` |

Ekranlar: KRTTBASV, KRTTGUNC, KRDTKULL, MUSTTANM, MUSTGUNC, HSPTVDSZ, ODMTTLMT, KRDTTAHS, PRMTGENL. `simulated` kolonu **yok**. KRDTERTL (E) bilerek katalogda yok.

### screen_departments ✅ (`screen_departments.json`, 23)
| Kolon | Açıklama | Örnek |
|---|---|---|
| screen_code | Ekran | `KRDTTAHS` |
| department_id | Departman | `KREDI_TAKIP` |
| role | `ana` / `etkilesimli` | `ana` |

Kural: PRMTGENL hariç her ekranın tek ana departmanı var; PRMTGENL'de 6 departman da etkileşimli (departman parametre grubundan belirlenir).

### error_handling_rules ✅ (`error_handling_rules.json`, 20 tohum)
| Kolon | Açıklama | Örnek |
|---|---|---|
| rule_id | Kural no | 7 |
| screen_code | Ekran ya da `*` (tüm ekranlar) | `ODMTTLMT` |
| error_number | Kibana hata numarası | 110731 |
| error_code | Hata kodu | `INSTITUTION_TIMEOUT` |
| error_type | `business` / `technical` | `technical` |
| department_id | Yönlenecek departman (boşsa ekranın ana departmanı) | `FATURA_ODEME` |
| open_incident | Çağrı açılsın mı (1/0) | 1 |
| explanation_hint | AI açıklamasına ipucu | … |
| source | `seed` / `mercek` | `seed` |
| status | `onerildi` / `onayli` / `reddedildi` | `onayli` |
| proposed_at, evidence_json | Mercek önerisi zamanı ve kanıtı | null |
| approved_by, approved_at | Onaylayan | null |
| hit_count | Eşleşme sayısı | 0 |

Hata numarası blokları: 11 ödeme · 12 kredi · 13 kart · 14 hesap · 15 müşteri · 16 parametre · 19 teknik. (screen_code, error_number) benzersiz. MUSTGUNC `PHONE_FORMAT_INVALID` bilerek yok (demoda Mercek önerir). **C kuralı:** kural `open_incident=0` dese de aynı ekran + kurum + hata için son 30 günde ≥ 50 hata varsa Mercek ana kayıt açar.

### closure_codes ✅ (`closure_codes.json`, 20 ana + 42 alt)
| Kolon | Açıklama | Örnek |
|---|---|---|
| code | Kod | `KURUM_SERVIS_KESINTISI` |
| name | Ad | Kurum Servis Kesintisi / Zaman Aşımı |
| parent_code | Ana kod (ana kodda null) | `DIS_KURUM_KAYNAKLI` |

### org_units 🟡 (eski `branches` + birimler)
| Kolon | Açıklama | Örnek |
|---|---|---|
| unit_id | Sayı; Kibana `BranchId` ile aynı | 101 |
| name | Ad | Kadıköy |
| unit_type | `S` şube · `G` genel müdürlük · `B` bölge | `S` |
| city | İl (G/B'de olabilir) | İstanbul |

İçerik: mevcut 5 şube (0101→101, 0102→102, 0601→601, 3501→3501, 9999 Dijital Şube); G tipi 90xx: Kredi Tahsilatları, Bireysel Krediler, Kart Ürünleri, Ödeme Sistemleri, Şube Operasyonları, Dijital Bankacılık, Müşteri Deneyimi, Uyum ve İç Kontrol; birkaç B bölge müdürlüğü. `branch_types` tablosu **yok**.

### institutions 🟡 (16)
| Kolon | Açıklama | Örnek |
|---|---|---|
| institution_code | Kod | `SU01` |
| name | Ad | İSKİ |
| bill_type | Fatura türü | Su |
| timeout_ms | Kurum zaman aşımı | 6000 |
| note | Not | |

Kaynak: `data/seed/catalog.json` → institutions (15) + **Gelir İdaresi `VRG01`**. Abone no uzunluğu alanı **bilerek yok** (C'nin kökü).

### institution_screens 🟡
| Kolon | Açıklama | Örnek |
|---|---|---|
| institution_code | Kurum | `SU01` |
| screen_code | Ekran (9 ekrandan) | `ODMTTLMT` |
| usage | `odeme` / `sorgu` / `gecmis` / `talimat` | `talimat` |

Not: eski taslakta ODMTFATR / ODMRGCMS / ODMTVRGI vardı; yeni katalogda bu ekranlar yok → fatura kurumları ODMTTLMT'ye bağlanır, Gelir İdaresi için uygun ekran yeni oturumda kullanıcıya sorulacak.

### channels 🟡
| Kolon | Açıklama | Örnek |
|---|---|---|
| channel_id | Kibana `ChannelId` | 1 |
| name | Ad | Şube |
| incident_channel | Çağrıdaki kanal karşılığı | `sube` |

Değerler: 1 Şube→sube · 2 Çağrı Merkezi→cagri_merkezi · 3 İnternet Şube→dijital · 4 Mobil→dijital · 5 Servis→null (çağrı açılmaz).

### incident_categories 🟡
| Kolon | Açıklama | Örnek |
|---|---|---|
| category | Kategori | Fatura talimatı |
| subcategory | Alt kategori | kurumdan yanıt alınamadı |
| screen_code | İlgili ekran; `*` tüm ekranlar | ODMTTLMT |

Kaynak: `catalog.json` → incident_categories (6 kategori). contacts kalktığı için yalnızca temaslarda kullanılan alt kategoriler (hatırlatma almadım, gecikme faizi itirazı, taksit sorusu, erteleme, erken kapama vb.) çağrılarda kullanılmıyorsa çıkarılır. Yeni ekranlara göre (talimat, tahsilat, parametre, müşteri tanımlama) alt kategoriler gözden geçirilir.

### scope_addons ⏳ (gözden geçirilecek)
Mevcut: addon_id, name, effort_md, main_share, customer_mgmt_share. 5 kayıt (ADD-SMS, ADD-PROAKTIF-SMS, ADD-GONDERIM-RAPOR, ADD-YETKI, ADD-PARAMETRE). Departman kavramıyla uyumlanmalı (ör. `department_shares_json`); `demands.mercek_suggestions_json.addon_id` buna bağlı.

---

## B. Ana tablolar

### customers 🟡 (40.000)
| Kolon | Açıklama | Örnek |
|---|---|---|
| customer_number | Müşteri no | `10000101` |
| full_name | Sentetik ad soyad | Umut Öztürk |
| segment | Bireysel / Premium / Özel Bankacılık | Bireysel |
| birth_date | Doğum tarihi (yaş sorguda hesaplanır) | 2006-03-14 |
| monthly_income | Aylık gelir | 28141 |
| city, district | İl, ilçe | İstanbul, Bakırköy |
| email | `@ornek.test` | umut.ozturk.0101@ornek.test |
| phone | `+90 5xx 000 xx xx` (sentetik) | +90 532 000 85 64 |
| perm_email, perm_sms, perm_phone | İletişim izinleri | 1 |

Kaldırılanlar: age, region_affected (bölge = city ∈ affected_region), address_changed_at (37 adres değişikliği MUSTGUNC loglarına taşınır), in_logs.

### loans 🟡 (33.000) — değişmedi
loan_id, customer_number, product, principal, remaining_principal, monthly_rate, term, installment, paid_installments, next_due_date, status (normal/gecikmede), delinquent_12m, collection_account.

### kibana_logs 🟡 (eski banking_logs)
| Kolon | Açıklama |
|---|---|
| log_id | Kayıt no (IDENTITY) |
| timestamp, log_time | Kibana `@timestamp` ve `LogTime` |
| log_level | Information / Warning / Error |
| app_name | `fineart` |
| application | Uygulama adı (ekrana göre değişir) |
| source_context | .NET sınıf adı |
| action_id, action_name | İşlem |
| request_path, referer, http_method, http_status_code | İstek bilgisi |
| is_business_exception | İş hatası mı |
| correlation_id | Her kayıtta dolu; incidents.kibana_correlation_id ile bağlanır |
| message | Log mesajı (bağlam burada: kurum, hane sayısı vb.) |
| exception_message, exception_source, exception_stack_trace | Hata |
| inner_exception_message / _source / _stack_trace | İç hata |
| app_exception_value | Uygulama hata değeri (hata numarası) |
| message_fields, message_filter, message_query_string, message_response | MessageObject alanları — **kişisel veri yok** |
| screen_id | Ekran kodu |
| branch_id | org_units.unit_id |
| branch_type | S / G / B |
| channel_id | channels.channel_id |
| call_id, client_id | İstemci / çağrı kimliği (sentetik) |
| user_name | Sentetik kullanıcı kodu |
| current_date | İşlem günü |
| customer_id, customer_branch_id | Müşteri no ve şubesi |
| session_id, session_start_date | Oturum |
| event_original | Ham kayıt (kişisel veri ve altyapı bilgisi temizlenmiş) |
| mercek_assigned_error_number | Mercek'in çözdüğü hata numarası |

Yok: kibana_index, request_id, source (demo kaydı = timestamp > 17.10 09:00), ClientIp, ServerInfo, ComputerName, ConnectionId, MachineId, ADUserName, CallerInfoJson, CommandInfo, ScreenOpeningMode, ScreenVersion, ZfuContext, BankId, BranchCountryId, Environment, @version, _score, _type, _index.

### incidents 🟡 (1.400 + demo)
| Kolon | Açıklama | Örnek |
|---|---|---|
| incident_id | Çağrı no | CAG-2051 |
| created_at | Açılış | |
| channel | sube / cagri_merkezi / dijital / is_birimi | sube |
| reporter_unit_id | org_units.unit_id | 601 |
| screen_code | Ekran | ODMTTLMT |
| category, subcategory | incident_categories | Fatura ödeme / kurumdan yanıt alınamadı |
| note | Bildirim notu (kişisel veri yok) | |
| customer_number | Müşteri | |
| kibana_correlation_id | Log bağlantısı | |
| department_id | Departman | FATURA_ODEME |
| mercek_assigned_error_code | Logda yoksa Mercek'in atadığı hata | |
| institution_code | Kurum | GAZ02 |
| master_incident_id | Ana kayıt (bağlı vakalar) | CAG-2051 |
| priority | 1–5 | 2 |
| status | acik / kapali | |
| solution_template_id | Hazır çözüm | SOL-031 |
| closure_code, sub_closure_code | closure_codes | DIS_KURUM_KAYNAKLI / KURUM_SERVIS_KESINTISI |
| resolution_note | O çağrının çözüm metni | |
| resolved_at | Kapanış | |
| enriched_json | Mercek zenginleştirmesi | |

Yok: subscriber_no, city, resolution_minutes. Kapanış ekranındaki "belirti", "Çağrı Konusu", "Çözüm Açıklaması" gerçek alan değil / doldurulmuyor.

### solution_templates 🟡 (eski solutions, 37)
| Kolon | Açıklama | Örnek |
|---|---|---|
| solution_template_id | Şablon no | SOL-031 |
| solution_text | Service Manager hazır çözüm metni | |
| closure_code, sub_closure_code | Önerilen kapanış | |
| department_id | Departman | FATURA_ODEME |
| mercek_assigned_title / _symptom / _root_cause / _steps (JSON) / _error_code | Mercek'in metinden çıkardıkları | |
| search_text | Hesaplanan (indexer) | |

### inbound_emails 🟡 (~35)
email_id, mailbox (`dis-paydas-duyuru@fineart.ornek.test`, tek ortak adres), received_at, from_address, from_display, subject, body_text, attachments_json, assigned_team, processing_status (yeni/inceleniyor/islendi/yok_sayildi), processed_by, processed_at, mercek_assigned_type (announcement/other), mercek_assigned_confidence, mercek_assigned_institution_code, mercek_assigned_summary, linked_announcement_id.
İçerik: 20 kurum duyurusu (18 işlenmiş + İSKİ 12.09 ve ASKİ işlenmemiş) + ~15 diğer (teşekkür, otomatik yanıt, yanlış adres). KVKK bulgusu olan mail `yok_sayildi`, Foundry'ye gitmez.

### announcements 🟡 (18 + demoda üretilenler)
ann_id, source_email_id, mercek_assigned_institution_code, published_at, mercek_assigned_effective_at, mercek_assigned_title, mercek_assigned_summary, mercek_assigned_screens_json, mercek_assigned_departments_json, mercek_assigned_impact, proposed_demand_id, status (onerildi/onayli/reddedildi), approved_by, approved_at, search_text.
C: İSKİ duyurusu burada **yok** (mailde bulunur). G: ASKİ (DUY-0419) → TLP-1045.

### demands 🟡 (eski requests, ~95 + 11 takvim talebi + demo)
demand_id (TLP-xxxx), created_at, demander_unit_id (org_units), origin (business_unit/mercek), source_announcement_id, title, description, status (oneri/analiz/planli/tamamlandi/iptal), type, components_json, screens_json, departments_json, planned_effort_md, actual_effort_md, planned_component_efforts_json, actual_component_efforts_json, planned_department_efforts_json, actual_department_efforts_json, decisions, analyst, approved_by, approved_at, planned_department_id, planned_from, planned_to, mercek_assigned_analysis_json, mercek_suggestions_json (addon_id, suggestion, evidence, effort_delta_md, date_impact, decision bekliyor/kabul/ret, decided_by, decided_at), mercek_suggestion_count (hesaplanan), search_text.
Yok: source_channel, scope_additions_json, TL maliyet. Efor yalnızca adam-gün; planned_* ≈ actual_*'ın %10–15 altında; bitmemişte actual_* boş. Ekran referansları 9 yeni ekrana dağıtılır. Senaryolar: D TLP-1043, E TLP-1044, G TLP-1045 (origin mercek, oneri).

### department_calendar 🟡
calendar_id (CAL-xxxx), department_id, demand_id (**zorunlu**), date_from, date_to, allocation_pct. `note` yok; talep dışı satır yok. Bugünkü 11 takvim satırı (`catalog.json` → service_calendar) planlı talep olarak demands'e eklenir (ör. TLP-1021 Yıl sonu regülasyon işi, KREDI_TAKIP 12.10–08.11 %100). Kapasite günde 1 a/g. D/E/G takvim sonuçları değişmemeli: 09.11→02.12/04.12 · 19.10→30.10/02.11 · 09.11→20.11.

### prevented_calls 🟡 (eski mercek_events)
prevented_id (IDENTITY), ts, user_name, screen_code, error_code, rule_id, kibana_correlation_id. `ai_usage` yok. Diğer metrikler kendi tablolarından sayılır.

### Kaldırılan tablolar
contacts (D ve E kanıtı loans/customers'tan), mercek_events, ai_usage, branch_types, services/screen_services/service_calendar (departman adlarıyla yeniden).

### JSON'da kalanlar (tablo değil)
demo_users (`department` → `unit`), affected_region (E; il adları arayüzde gösterilmez), _meta (veri sonu 2026-10-17 09:00 +03, seed 42).
