import os
from typing import Optional, List

from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import Response
from pydantic import ConfigDict, BaseModel, Field, EmailStr
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated

from bson import ObjectId
import asyncio
from pymongo import AsyncMongoClient
from pymongo import ReturnDocument

# ------------------------------------------------------------------------ #
#                         Inicialització de l'aplicació                    #
# ------------------------------------------------------------------------ #
# Creació de la instància FastAPI amb informació bàsica de l'API
app = FastAPI(
    title="Student Course API",
    summary="Exemple d'API REST amb FastAPI i MongoDB per gestionar informació d'estudiants",
)

# ------------------------------------------------------------------------ #
#                   Configuració de la connexió amb MongoDB                #
# ------------------------------------------------------------------------ #
# Creem el client de MongoDB utilitzant la URL de connexió emmagatzemada
# a les variables d'entorn. Això evita incloure credencials dins del codi.
mongodb_url = "mongodb+srv://miguel_admin:12345@cluster0.letwcvl.mongodb.net/?appName=Cluster0"
client = AsyncMongoClient(mongodb_url)

# Selecció de la base de dades i de la col·lecció
db = client.cine_db
movie_collection = db.get_collection("peliculas")

#-----Model Pydantic----

# Els documents de MongoDB tenen `_id` de tipus ObjectId.
# Aquí definim PyObjectId com un string serialitzable per JSON,
# que serà utilitzat als models Pydantic.
PyObjectId = Annotated[str, BeforeValidator(str)]

# ------------------------------------------------------------------------ #
#                            Definició dels models                         #
# ------------------------------------------------------------------------ #
class MovieModel(BaseModel):
    # Clau primària de la pelicula
    # MongoDB utilitza `_id`, però l'API exposa aquest camp com `id`.
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    
    # Camps obligatoris que te la pelicula
    titol: str = Field(...) #Titol de la peli
    descripcio: str = Field(...) # Descripcio de la peli
    estat: str = Field(default="pendent de vore") #Si hem vist la peli o no
    puntuacio: int = Field(..., ge=1, le=5) #Valoracio de la peli
    genere: str = Field(...) #El genere de la peli
    usuari: str = Field(...) #Quin usuari volem vore la informacio

    # Configuració addicional del model Pydantic
    model_config = ConfigDict(
        populate_by_name=True,  # Permet utilitzar alias al serialitzar/deserialitzar
        arbitrary_types_allowed=True,  # Permet tipus personalitzats com ObjectId
        json_schema_extra={
            "example": {
                "titul": "Spiderman I",
                "descripcio": "Un adolescent que li pique una aranya al coll i es converteix en un superheroi",
                "estat": "vista",
                "puntuacio": 5,
                "genere": "Ciencia Ficcio",
                "usuari": "Miguel"
            }
        },
    )
#------- Endpoints (Rutes) ------------

#Aqui crearem la ruta de peticions tipo POST
@app.post ("/peliculas/", response_model=MovieModel, status_code=status.HTTP_201_CREATED)
async def crear_pelicula(pelicula: MovieModel = Body(...)): # Creem la funcio asincrona per a crear pelicules
    nova_pelicula = pelicula.model_dump(by_alias = True, exclude=["id"]) #Convertim l'objecte en un diccionari
    resultat = await movie_collection.insert_one(nova_pelicula) #Aqui agafa el diccionari i el guarda al cluster de MongoDB Atlas
    pelicula_creada = await movie_collection.find_one({"_id":resultat.inserted_id}) # Busquem el resultat
    return pelicula_creada #I una vegada buscat el resultat ens el retorne

#Ara aqui creem la ruta per a peticions tipo GET
@app.get ("/peliculas/", response_description="Llista totes les pelicules", response_model=List[MovieModel])
async def llistar_pelicules(): #Creem la funcio asincrona de llistar_pelicules
    llista_pelicules = await movie_collection.find().to_list(1000) #Aqui li diem que busco les 1000 primeres pelicules
    return llista_pelicules # I per ultim nos les retorna

#Creem la ruta per a fer UPDATE
@app.put("/peliculas/{id}", response_model=MovieModel)
async def actualitzar_partida(id: str, pelicula: MovieModel = Body(...)): #Creem la funcio asincrona per actulitar les dades
    dades_actualitzades = pelicula.model(by_alias=True, exclude=["id"]) #Convertim les dades que hem posats a un diccionari
    resultat = await movie_collection.find_one_and_update( #Aqui li diem que busco el id que hem modificat
        {"_id": ObjectId(id)},
        {"$set": dades_actualitzades}, #I despues aqui actulitzaria les dades
        return_document=ReturnDocument.AFTER # I ens retorna la pelicula
    )
    if resultat:
        return resultat # Si ens troba el id ho retornarem per el navegador
    raise HTTPException(status_code=404, detail=f"Pelicula {id} no trobada") #Si no ens surtira el seguent error

# Creem la ruta per a fer el DELETE
@app.delete("/pelicules/{id}", response_description="Esborra una pelicula")
async def borrar_pelicula(id: str): #Fem una funcio asincrona anomenada borrar_pelicula
    resultat_borrat = await movie_collection.delete_one({"_id": ObjectId(id)}) #Intentarem borrar la pelicula amb el id que li donarem
    if resultat_borrat.delete_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT) #Si hem pogut esborrar el rsultat executara aixo que vol dir que estara ben fet
    raise HTTPException(stauts_code=404, detail=f"No s'ha pogut esborrar: ID {id} no existeix") # Si no podem borrarlo surtira este error

#Creem la ruta per a fer un PATCH i cambiar el estat de les peli
@app.patch("/peliculas/{id}/estado", response_model=MovieModel)
async def cambiar_estado_pelicula(id: str, nuevo_estado: str = Body()): #Fem la funcio asincrona
    resultat = await movie_collection.find_one_and_update( #find_one_and_update busca el document y el actualitza
        {"_id": ObjectId(id)}, #Busca el id que li hem donat
        {"$set": {"estado": nuevo_estado}}, #Cambia el estat de la pelicula depen lo que li diguesem si vist o no vist
        return_document = ReturnDocument.AFTER #Ens retorna la pelicual
    )
    if resultat:
        return resultat # Si tot a funcionat correctament ens retorna la pelicula
    raise HTTPException(status_code=404, detail=f"No se ha encontrado la pelicula") # Si surt malament en surtira este error