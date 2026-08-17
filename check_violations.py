import duckdb

P = "data/bronze/dt=*/pitches.parquet"
con = duckdb.connect()

print("== 위반 18건의 패턴 ==")
print(con.sql(f"""
    select balls, strikes, result, count(*) as n
    from '{P}'
    where balls not between 0 and 3 or strikes not between 0 and 2
    group by all order by n desc
"""))

print("== 위반 행의 텍스트 샘플 ==")
print(con.sql(f"""
    select pitch_seq_in_game, balls, strikes, result, text
    from '{P}'
    where balls not between 0 and 3 or strikes not between 0 and 2
    limit 8
"""))
