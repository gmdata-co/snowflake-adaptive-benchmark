
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select query_num
from "benchmark_results"."main"."platform_comparison_coldstart"
where query_num is null



  
  
      
    ) dbt_internal_test