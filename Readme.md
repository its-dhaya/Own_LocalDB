//database creation
create database_name
//example
create mydb

//accessing database
use database_name
//example
use mydb   

//exiting the current database
exit database_name
//example
exit mydb

//table creation
make table_name
//example
make users

//data insertion 
include table_name {"key":"value"}
//example
include users [{"name":"John", "age":"30","email":"john@example.com"}]


//get data
select table_name
select table_name field_name
//example
select users
select users name

//deleting a specific field 
delete field_name from table_name where condition
//example
delete name from users where age=30

//void which similar to drop
exclude from table_name where condition
exclude from table_name 
exclude  table_name
//example
exclude from users where name = John
exclude from users
exclude users

//update 
update table_name set field_name = new_value where condition
//example
update users set name = "Bob" where age=30

//count
count table_name
//example
count users

//delete database
remove database_name 

//exiting current database
//exit database_name

//exiting the simpledb
exit


