
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        status as value_field,
        count(*) as n_records

    from "benchmark_results"."main"."platform_comparison_latest"
    group by status

)

select *
from all_values
where value_field not in (
    'success','snowflake_error','databricks_error','both_error','unknown','TOTAL'
)



  
  
      
    ) dbt_internal_test