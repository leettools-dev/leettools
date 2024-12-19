# Different Pydantic models in each schema

Here is the main idea of using different pydantic models for different APIs:

- XBase:     the essential fields needed for all other models
- XCreate:   (parent XBase) the fields required for creating a new object
- XInDBBase: (parent XCreate or XBase) the fields are shared by the XUpdate and XInDB.
              Sometimes we do not need this intermediate model.
- XUpdate:   (parent XBase or XCreate or XInDBBase depending the semantics) the fields
             that can be updated through the GENERIC update API for the object, usually
             we need the UUID (or any primary key fields) here. The API will look up by
             the primary key and update all other fields specified in the XUpdate. Some
             special derived fields need to be updated through special APIs.
- XInDB:     (parent XInDBBase) the fields that are actually stored in the database
- X:         (parent XInDB or XBase) the fields that are returned by the API and used 
             by the applications.

So for the CRUD APIs, we use different Pydantic models for different purposes:
- Create: input=XCreate -> save to XInDB -> return=X
- Read:   input=filter -> find xInDB -> return=X
- Update: input=XUpdate -> find XInDB from primary key in XUpate -> update XInDB -> return=X
- Delete: input=filters -> find XInDB with filter -> delete XInDB -> return=none

The XUpdate model is used to simplify the update API so that we do not need to provide
all the fields in the XInDB model.