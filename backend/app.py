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
@app.post ("/movies/", response_model=MovieModel, status_code=status.HTTP_201_CREATED)
async def create_movie(movie: MovieModel = Body(...)): # Creem la funcio asincrona
    new_movie = movie.model_dump(by_alias = True, exclude=["id"]) #Convertim l'objecte en un diccionari
    result = await movie_collection.insert_one(new_movie) #Aqui agafa el diccionari i el guarda al cluster de MongoDB Atlas
    new_movie["_id"] = result.inserted_id
    return new_movie #I una vegada guardad ens retornara l'ID per sabre que ho a guardat

#Definim una altra ruta per als gets
@app.get("/movies/", response_model=List[MovieModel])
async def list_movies(): #Creem la funcio asincrona
    movies = await movie_collection.find().to_list(1000) #Despues li direm que busco les pelicules i que les mostro en forma de llista, nomes les 1000 primeres
    return movies
