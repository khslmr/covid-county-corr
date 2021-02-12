## COVID-19 County Correlations

A casual project that searches for a relation between COVID-19 statistics (cases and deaths) and a wide array of county demographic, political, and climate data.  

*Disclaimer: I am not an expert in epidemiology and you should not interpret any analysis here as medical advice!*


### About

My primary goals for this project are to gain experience 1) manipulating inhomegenous datasets and 2) exploring various machine learning tools.  To make it interesting, I decided to investigate publicly available COVID-19 data.

In terms of the subject matter, the overarching question for this project is: "Does there exist any link between the various long-term qualities of a county/region and its susceptibility to COVID-19?  Which qualities are most relevant?"  For example, we know that African Americans experience COVID-19 [more severely](https://www.cidrap.umn.edu/news-perspective/2020/08/us-blacks-3-times-more-likely-whites-get-covid-19) than whites, but is skin color the real difference here or do other demographics play a role?  Indeed, a greater percentage of blacks than whites live in urban environments, are below the federal poverty level, and won't graduate from college.  Taking one of these points, if COVID-19 happens to affect lower income individuals more severely, then on average blacks will appear to suffer disproportionately even if COVID-19 impacts all races equally!

Another interesting possibility is the intersection between politics and COVID-19.  One plausible hypothesis is that Trump supporters in 2020 are less likely to wear a mask (Trump often refused to wear one) than Biden supporters, perhaps indicating a greater fraction of the former are indifferent about health protocols (see this interesting [related article](https://www.pnas.org/content/117/39/24144)).  If this is true, we might expect to see COVID-19 affect a higher fraction of Trump voters.  On the other hand, state governments' reponse to the pandemic (i.e., their implementation of various safety protocols) has varied wildly, especially in the early months, and it seems logical to explore how politics at this level might have [slowed or encouraged](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7587838/) the spread of COVID-19.


### Data

The data for this project come from a number of different sources, with varying levels of detail.  In some cases (e.g., unemployment rates, recorded temperatures) I had to consolidate the time axis in order to match the other non-temporal data.  In other cases (e.g., population and education) the data were subdivided into more racial and/or age categories than were helpful.  Hence, the choice of data collected here can only be described as "ad hoc" as there is no particular reason why any features have been included or excluded.  Indeed, I may add new features that seem relevant to future versions of the dataset.

The full dataset includes 28 features plus 4 fields describing COVID-19 cases and 4 more for COVID-19 deaths, with one row for each of 3141 counties, cities and their equivalents across the U.S.  Documentation about specific data sources can be found in the commented lines in the `clean_and_concat.py` file, which also provides the code used to compile the data into one file.  The `county_covid_and_demo_data.csv` file contains the cleaned dataset.


### Models

This is a work in progress.  I intend to collect my modeling explorations (as they come) into the `/models` folder as Jupyter notebooks, which Github will automatically render for you.
