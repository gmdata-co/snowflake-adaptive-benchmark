
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select scenario
from "benchmark_results"."main"."platform_comparison_latest"
where scenario is null



  
  
      
    ) dbt_internal_test