import duckdb

P = "data/bronze/dt=*/pitches.parquet"
con = duckdb.connect()

print("== 1. 총 행 수 ==")
print(con.sql(f"select count(*) as rows from '{P}'"))

print("== 2. null 개수 ==")
print(con.sql(f"""
    select count(*) filter (where balls is null)    as null_balls,
           count(*) filter (where strikes is null)  as null_strikes,
           count(*) filter (where velocity is null) as null_velo,
           count(*) filter (where result is null)   as null_result,
           count(*) filter (where pitch_type is null) as null_type
    from '{P}'
"""))

print("== 3. 볼카운트 규칙 위반 ==")
print(con.sql(f"""
    select count(*) as violations from '{P}'
    where balls not between 0 and 3 or strikes not between 0 and 2
"""))

print("== 4. 이닝별 투구 수 ==")
print(con.sql(f"select inning, count(*) as pitches from '{P}' group by inning order by inning"))

print("== 5. 구속 범위 ==")
print(con.sql(f"select min(velocity) as v_min, max(velocity) as v_max from '{P}'"))
