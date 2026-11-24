INSERT INTO rehearsal_venues VALUES
 ('PIER','潮埠露天台',false,24,0,'沿堤线'),('CEN','下街廊馆',true,20,3800,'沿堤线'),
 ('SIDE','巷口小廊',true,8,3000,'沿堤线') ON CONFLICT DO NOTHING;
INSERT INTO practice_holds VALUES
 ('H-12','八月第 3 轮主队','2026-08-12','PIER','CEN',30,34,14,'held'),
 ('H-14','暑期同场试鼓','2026-08-12','PIER','CEN',31,33,10,'held'),
 ('H-16','街角结曲小组','2026-08-12','PIER','SIDE',30,34,10,'held'),
 ('H-20','暑期尾场无完整气象','2026-08-13','PIER','CEN',30,34,14,'held')
 ON CONFLICT DO NOTHING;
INSERT INTO historical_blocks
 SELECT day::date,half,
 CASE WHEN half=28 THEN 30+i%3 WHEN half=29 THEN 31+i%2
      WHEN half=30 THEN 33+i%2 WHEN half=31 THEN 35+i%3
      WHEN half=32 THEN 36+i%3 ELSE 33+i%2 END,
 61+i%4, '堤台半小时回放-'||day::date::text||'.csv'
 FROM (
   SELECT '2026-08-01'::date + i AS day,i FROM generate_series(0,12) i
 ) periods CROSS JOIN generate_series(28,33) half
 WHERE NOT (day='2026-08-13' AND half=29) ON CONFLICT DO NOTHING;
