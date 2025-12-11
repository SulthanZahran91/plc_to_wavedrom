#!/usr/bin/env python3
import os

# ==============================================================================
# CONFIG — EDIT ONLY THIS BLOCK
# ==============================================================================

# 1. Add your database names here
DB_LIST = [
    "ECPDB_1",
    "ECPDB"
]

# 2. General Table/Schema Info
SCHEMA = "dbo"
TABLE = "FBDRIVER"

# 3. Key column to FIND/JOIN ON
KEY_COLUMN = "DRIVERTYPE"
KEY_TYPE = "nvarchar(128)" # Type for DRIVERTYPE

# 4. Columns to SET
# This column will be set from 'keyNew' in the JSON
NEW_KEY_COLUMN = "DRIVERNO"
NEW_KEY_TYPE = "int"

# These columns will be set from 'v1', 'v2', 'v3'
COL1 = "OPENRETRYSEC"
COL1_TYPE = "int"

COL2 = "TIMEOUTSEC"
COL2_TYPE = "int"

COL3 = "USEFLAG"
COL3_TYPE = "char"

# 5. The JSON steps to execute, based on your new logic.
#    keyOld = DRIVERTYPE (string)
#    keyNew = new DRIVERNO (int)
#    v1 = OPENRETRYSEC (int)
#    v2 = TIMEOUTSEC (int)
#    v3 = USEFLAG (char)
#
# Per your instructions:
# - MELSECNET:  keyNew=10, v3='T', step=1
# - OPC.UA:     keyNew=11, v3='T', step=2
# - SIMULATION: keyNew=1,  v3='T', step=3
# (I have assumed v1=2 and v2=86400 are still desired, as in the original script)

STEPS_JSON = r"""
[
  {"step":1, "keyOld": "MELSECNET", "keyNew": 10, "v1": 2, "v2": 86400, "v3": "T"},
  {"step":2, "keyOld": "OPC.UA",    "keyNew": 11, "v1": 2, "v2": 86400, "v3": "T"},
  {"step":3, "keyOld": "SIMULATION","keyNew": 1,  "v1": 2, "v2": 86400, "v3": "T"}
]
"""

# 6. Output Filename
OUTPUT_FILENAME = "generated_update_script_v3.sql"

# ==================== END CONFIG — NO CHANGES BELOW THIS LINE ==============

def generate_script():
    """
    Generates the full, static T-SQL script from the config.
    """
    print("Starting T-SQL script generation (v3)...")
    
    # This list will hold all the pieces of our final script
    sql_script_parts = []

    # --- 1. Pre-calculate dynamic T-SQL parts ---
    
    # Helper fragments for CONVERT
    conv_key = f"CONVERT({KEY_TYPE}, "
    conv_new_key = f"CONVERT({NEW_KEY_TYPE}, "
    conv1 = f"CONVERT({COL1_TYPE}, "
    conv2 = f"CONVERT({COL2_TYPE}, "
    conv3 = f"CONVERT({COL3_TYPE}, "

    # Build the final SET clause to set all 4 columns
    final_set_clause = f"""
           [{NEW_KEY_COLUMN}] = {conv_new_key}s.keyNew),
           [{COL1}] = {conv1}s.v1),
           [{COL2}] = {conv2}s.v2),
           [{COL3}] = {conv3}s.v3)
    """

    # Build the OPENJSON WITH clause
    openjson_with_clause = f"""
      step   int               '$.step',
      keyOld {KEY_TYPE}    '$.keyOld',
      keyNew {NEW_KEY_TYPE}    '$.keyNew',
      v1     {COL1_TYPE}    '$.v1',
      v2     {COL2_TYPE}    '$.v2',
      v3     {COL3_TYPE}    '$.v3'
    """

    # --- 2. Add the T-SQL Script Header ---
    sql_script_parts.append(f"""
PRINT N'--- Starting generated update script (v3) ---';
SET XACT_ABORT, NOCOUNT ON;

-- This log table will hold results from all databases.
IF OBJECT_ID('tempdb..#log') IS NOT NULL DROP TABLE #log;
CREATE TABLE #log(
    db sysname,
    status varchar(8),
    rows int NULL,
    errnum int NULL,
    errmsg nvarchar(2048) NULL
);
""")

    # --- 3. Loop through each DB and generate its T-SQL block ---
    for db_name in DB_LIST:
        print(f"  -> Generating block for database: [{db_name}]")
        
        # This is the template for each database's unique block of code
        db_block = f"""
PRINT N'--- Processing Database: [{db_name}] ---';

BEGIN TRY
    -- Check if the target table exists in this database
    IF EXISTS (SELECT 1 FROM [{db_name}].sys.tables t
               JOIN [{db_name}].sys.schemas s ON s.schema_id=t.schema_id
               WHERE s.name = N'{SCHEMA}' AND t.name = N'{TABLE}')
    BEGIN
        PRINT N'  -> Table [{SCHEMA}].[{TABLE}] found in [{db_name}]. Starting transaction...';
        BEGIN TRAN;
        
        -- Define JSON data *inside* the batch
        DECLARE @jsonData nvarchar(max) = N'{STEPS_JSON.strip()}';

        -- Parse the JSON data
        DECLARE @S TABLE(step int, keyOld sql_variant, keyNew sql_variant, v1 sql_variant, v2 sql_variant, v3 sql_variant);
        INSERT @S(step, keyOld, keyNew, v1, v2, v3)
        SELECT j.step, j.keyOld, j.keyNew, j.v1, j.v2, j.v3
        FROM OPENJSON(@jsonData)
        WITH (
            {openjson_with_clause}
        ) AS j;

        DECLARE @r1 int=0, @r2 int=0, @r3 int=0, @rowz int;

        -- Step 1 (MELSECNET)
        PRINT N'  -> Executing Step 1 (MELSECNET)...';
        ;WITH s AS (SELECT TOP (1) * FROM @S WHERE step=1)
        UPDATE T
           SET {final_set_clause}
        FROM [{db_name}].[{SCHEMA}].[{TABLE}] AS T
        JOIN s ON T.[{KEY_COLUMN}] = {conv_key}s.keyOld);
        
        SET @rowz = @@ROWCOUNT;
        IF @rowz<>1 THROW 50001, 'Step 1 (MELSECNET) affected unexpected rows', 1;
        SET @r1=@rowz;
        PRINT N'  -> Step 1 complete (' + CAST(@r1 AS varchar(10)) + ' row affected).';

        -- Step 2 (OPC.UA)
        PRINT N'  -> Executing Step 2 (OPC.UA)...';
        ;WITH s AS (SELECT TOP (1) * FROM @S WHERE step=2)
        UPDATE T
           SET {final_set_clause}
        FROM [{db_name}].[{SCHEMA}].[{TABLE}] AS T
        JOIN s ON T.[{KEY_COLUMN}] = {conv_key}s.keyOld);
        
        SET @rowz = @@ROWCOUNT;
        IF @rowz<>1 THROW 50002, 'Step 2 (OPC.UA) affected unexpected rows', 1;
        SET @r2=@rowz;
        PRINT N'  -> Step 2 complete (' + CAST(@r2 AS varchar(10)) + ' row affected).';

        -- Step 3 (SIMULATION)
        PRINT N'  -> Executing Step 3 (SIMULATION)...';
        ;WITH s AS (SELECT TOP (1) * FROM @S WHERE step=3)
        UPDATE T
           SET {final_set_clause}
        FROM [{db_name}].[{SCHEMA}].[{TABLE}] AS T
        JOIN s ON T.[{KEY_COLUMN}] = {conv_key}s.keyOld);
        
        SET @rowz = @@ROWCOUNT;
        IF @rowz<>1 THROW 50003, 'Step 3 (SIMULATION) affected unexpected rows', 1;
        SET @r3=@rowz;
        PRINT N'  -> Step 3 complete (' + CAST(@r3 AS varchar(10)) + ' row affected).';

        COMMIT;
        PRINT N'  -> Transaction committed.';
        INSERT INTO #log VALUES (N'{db_name}', 'OK', @r1+@r2+@r3, NULL, NULL);
    END
    ELSE
    BEGIN
        -- Table was not found
        PRINT N'  -> Table [{SCHEMA}].[{TABLE}] NOT found in [{db_name}]. Logging as SKIP.';
        INSERT INTO #log VALUES (N'{db_name}', 'SKIP', NULL, NULL, N'Table {SCHEMA}.{TABLE} not found');
    END
END TRY
BEGIN CATCH
    PRINT N'  -> *** ERROR OCCURRED ***';
    PRINT N'  -> Error: ' + ERROR_MESSAGE();
    IF XACT_STATE()<>0
    BEGIN
        PRINT N'  -> Transaction is uncommittable. Rolling back...';
        ROLLBACK;
    END
    INSERT INTO #log VALUES (N'{db_name}', 'FAIL', NULL, ERROR_NUMBER(), ERROR_MESSAGE());
END CATCH;
GO
"""
        sql_script_parts.append(db_block)

    # --- 4. Add the T-SQL Script Footer ---
    sql_script_parts.append(f"""
PRINT N'------------------------------------------------------------';
PRINT N'Update script complete. Final Results:';

SELECT
    db,
    status,
    rows,
    errnum,
    errmsg
FROM #log
ORDER BY
    CASE status WHEN 'FAIL' THEN 0 WHEN 'OK' THEN 1 ELSE 2 END,
    db;

DROP TABLE #log;

PRINT N'--- End of script ---';
""")

    # --- 5. Write the final script to a file ---
    final_script = "\n".join(sql_script_parts)
    
    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(final_script)
        
        print(f"\n✅ Success! \n")
        print(f"Generated script saved to: {os.path.abspath(OUTPUT_FILENAME)}")
        print("You can now open this file in SSMS and run it.")
        
    except Exception as e:
        print(f"\n❌ Error writing file: {e}")

# --- Run the script ---
if __name__ == "__main__":
    generate_script()