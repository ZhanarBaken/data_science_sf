# <p style="border:3px solid DodgerBlue;text-align:center;font-size:100%;">WHAT CASE DO WE DECIDE?  </p> 
   
# Astana Real Estate Price Estimation Chatbot

## Introduction
Welcome to my Notebook for Real Estate Price Estimation in Astana!

In this notebook, I present a comprehensive approach to estimating real estate prices in Astana, Kazakhstan. Leveraging the power of Python and various libraries, I have developed a robust system that utilizes data from multiple sources to provide accurate price predictions.

Throughout the implementation, I incorporated the following key components:

* Data Acquisition from krisha.kz:
I gathered extensive real estate data from krisha.kz, one of the leading platforms for property listings in Kazakhstan. This data serves as the foundation for my price estimation model, encompassing a wide range of properties across Astana.

* Geocoding with 2GIS:
Utilizing geocoding services provided by 2GIS, I accurately pinpoint the geographical locations of properties within Astana. This crucial step enables me to incorporate spatial information into my analysis, enhancing the precision of my price estimations.

* Distance Calculation using Geopy:
By employing the Geopy library, I calculate distances between properties and various amenities, landmarks, and essential facilities in Astana. This feature adds value to my price estimations by considering proximity to key locations, which significantly influences property values.

* Information Retrieval from kn.kz:
Extracting pertinent details about residential complexes from kn.kz, I enrich my dataset with additional insights into neighborhood characteristics, amenities, and community features. This information contributes to a more comprehensive understanding of the factors affecting property prices in Astana.

By synergizing these tools and data sources, my notebook offers a sophisticated solution for estimating real estate prices in Astana. Through detailed code demonstrations and insightful analysis, I aim to provide valuable insights to stakeholders in the Astana housing market.


# <p style="border:3px solid DodgerBlue;text-align:center;font-size:100%;">Let's look at the data. </p> 
    
<table > 

   <tr>
    <th>Column</th>
    <th>Description</th>
    <th>Type</th>
  </tr>
  
   <tr>
    <td>price</td>
    <td>the total cost of the apartment</td>
    <td>int64</td>
  </tr>

   <tr>
    <td>owner</td>
    <td>ad from a realtor or from the property owner</td>
    <td>object</td>
  </tr>

   <tr>
    <td>complex_name</td>
    <td>name of residential complexes</td>
    <td>object</td>
  </tr>

   <tr>
    <td>house_type</td>
    <td>describes the materials used in the construction of the house</td>
    <td>object</td>
  </tr> 
    
  <tr>
    <td>in_pledge</td>
    <td>a boolean feature indicating whether the apartment is pledged or not</td>
    <td>bool</td>
  </tr>
    
  <tr>
    <td>construction_year</td>
    <td>the year of construction of the house</td>
    <td>int64</td>
  </tr>
    
   <tr>
    <td>ceiling_height</td>
    <td>the ceiling height in the apartment</td>
    <td>float64</td>
  </tr>

   <tr>
    <td>bathroom_info</td>
    <td>number of bathrooms in the apartment</td>
    <td>object</td>
  </tr>
    
   <tr>
    <td>condition</td>
    <td>the type of finishing in the apartment</td>
    <td>object</td>
  </tr> 
   
   <tr>
    <td>area</td>
    <td>the area of the apartment</td>
    <td>float64</td>
  </tr>  
    
   <tr>
    <td>room_count</td>
    <td>the number of rooms in the apartment</td>
    <td>int64</td>
  </tr>  
    
   <tr>
    <td>floor</td>
    <td>the floor on which the apartment is located</td>
    <td>int64</td>
  </tr> 
    
   <tr>
    <td>floor_count</td>
    <td>the number of floors in the building</td>
    <td>int64</td>
  </tr> 
    
  <tr>
    <td>district</td>
    <td>the name of the district where the building is located</td>
    <td>object</td>
  </tr> 

   <tr>
    <td>complex_class</td>
    <td>the housing class</td>
    <td>object</td>
  </tr> 
    
   <tr>
    <td>parking</td>
    <td>information about the presence and type of parking</td>
    <td>object</td>
  </tr> 
    
   <tr>
    <td>elevator</td>
    <td>information about the presence of an elevator in the building</td>
    <td>object</td>
  </tr> 
    
   <tr>
    <td>schools_within_500m</td>
    <td>the number of schools within a radius of 500 meters</td>
    <td>float64</td>
  </tr> 
    
   <tr>
    <td>kindergartens_within_500m</td>
    <td>the number of kindergartens within a radius of 500 meters</td>
    <td>ifloat64</td>
  </tr> 
    
   <tr>
    <td>park_within_1km</td>
    <td>the presence of a park within a kilometer radius</td>
    <td>bool</td>
  </tr> 
    
   <tr>
    <td>coordinates</td>
    <td>the coordinates of the residential building (latitude, longitude)</td>
    <td>object</td>
  </tr> 
    
   <tr>
    <td>distance_to_center</td>
    <td>the distance to the city center in kilometers</td>
    <td>float64</td>
  </tr> 
    
   <tr>
    <td>distance_to_botanical_garden</td>
    <td>the distance to the botanical park in kilometers</td>
    <td>float64</td>
  </tr> 
 
   <tr>
    <td>distance_to_triathlon_park</td>
    <td>the distance to the triathlonl park in kilometers</td>
    <td>float64</td>
  </tr>
  <tr>
    <td>distance_to_astana_park</td>
    <td>the distance to the central astana park in kilometers</td>
    <td>float64</td>
  </tr>
  <tr>
    <td>distance_to_treatment_facility</td>
    <td>the distance to the waste treatment facility in kilometers</td>
    <td>float64</td>
  </tr>
  <tr>
    <td>distance_to_railway_station_1</td>
    <td>the distance to the first railway station on the right bank in kilometers</td>
    <td>float64</td>
  </tr>
  <tr>
    <td>distance_to_railway_station_2</td>
    <td>the distance to the second railway station on the left bank in kilometers</td>
    <td>float64</td>
  </tr>
  <tr>
    <td>distance_to_industrial_zone</td>
    <td>the distance to the industrial zone in kilometers</td>
    <td>float64</td>
  </tr>
  <tr>
    <td>kzt_sq_m</td>
    <td>the price per square meter in Kazakh Tenge (KZT)</td>
    <td>float64</td>
  </tr>
  <tr>
    <td>last_floor</td>
    <td>a boolean feature indicating whether the floor is the last one or not</td>
    <td>bool</td>
  </tr>
  <tr>
    <td>first_floor</td>
    <td>a boolean feature indicating whether the floor is the first one or not</td>
    <td>bool</td>
  </tr>

</table>

</font>

# <p style="border:3px solid DodgerBlue;text-align:center;font-size:100%;">Stages of the project. </p> 

1. Data Parsing

2. Handling Missing Values and Feature Engineering

3. Data Analysis

4. Encoding

5. Model Training (in progress)