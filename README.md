# Trumpf: Flexible Job Shop Scheduling with Quantum Computing

#### GitLab Space for both teams: Quantum Annealing & Gate Model 


### Overview

1. Problem Understanding and QUBO Formulation
1. Quantum Annealing
1. Quantum Gate Model
1. Results, Comparison and Conclusion
1. Final Paper
1. Sources


### Content

<img src="https://milani.ch/assets/Logo/Trumpf-logo.svg" alt=" drawing" width="200"/>

#### Unternehmen

Die Trumpf-Gruppe ist ein Unternehmen mit Hauptsitz in Ditzingen nahe Stuttgart. Trumpf gehört zu den weltweit größten Anbietern von Werkzeugmaschinen. Mit mehr als 70 operativen Tochtergesellschaften ist die Trumpf-Gruppe weltweit in allen wichtigen Märkten vertreten. Produktionsstandorte befinden sich in Deutschland, China, Frankreich, Großbritannien, Italien, Japan, Mexiko, Österreich, Polen, in der Schweiz, in Tschechien und in den USA.


#### Flexible Job Shop Scheduling Problem für das QAR Lab

In der flexiblen Blechfertigung werden kaum Großserienteile gefertigt, sondern eher kleinere Stückzahlen. Oftmals sind die Betriebe Lohnfertiger. Zuerst werden Rohbleche (Standardmaß 3000 x 1500 mm) mit einem trennenden Verfahren, oftmals Laserschneiden, in die zu produzierenden Teile geteilt. Da fertige Blechprodukte nur seltenen Fällen aus 2- dimensionalen Teilen bestehen, sind im Anschluss noch weitere Bearbeitungsverfahren notwendig. Im Folgenden soll die Betrachtung auf Biegen, Schweißen und Lackieren beschränkt werden. Um die Abhängigkeit der Bearbeitungsarten untereinander möglichst klein zu halten, kann ein Halbfertigteile-Lager zwischen den trennenden Verfahren und den weiteren Bearbeitungsschritten benutzt werden. Die Teile fließen dann ohne ein weiteres Lager durch diese Bearbeitungsstationen.


Nach dem Halbfertigteile-Lager entsteht in der Produktionsplanung ein Job Shop Scheduling Problem. Es muss eine Antwort auf die Frage gefunden werden, wann welches Teil auf welcher Maschine bearbeitet werden soll. Die Bearbeitungsstationen sind dabei in der Reihenfolge Biegen, Schweißen, Lackieren zu durchlaufen. Die Transportzeit der Teile zwischen den Stationen sowie die kurzzeitige Lagerung auf Logistikwägen soll vernachlässigt werden.



#### Die Daten

Die Produktionszeit beginnt bei 0 und zählt diskret in Minuten aufwärts. Es gibt 3 Biegemaschinen und jede Biegelinie dauert 20 Sekunden. Es gibt außerdem 2 Schweißanlagen, die jeweils 30 Sekunden für einen Schweißpunkt brauchen. Die Angaben in den Daten sind als Anzahl der Biegelinien und Schweißpunkte zu verstehen. Da die Maschinen sich gleich verhalten, könnten sie auch zusammengefasst werden. Die Fertigung hat außerdem eine Lackierzelle, deren Bearbeitungszeit für jedes Teil direkt in Minuten angegeben ist. Im Beispieldatensatz ist jede Zeile als ein Teil zu verstehen. Jedes Teil gehört dabei zu einer Order, wobei eine Order aus mehreren Teilen bestehen kann. Diese haben dann dasselbe Fälligkeitsdatum. Im JSSPDataGenerator.py finden Sie einen möglichen Generator für Beispieldaten. Wählen Sie die Bearbeitungszeiten so, dass bestimmte Stationen im Durchschnitt besonders voll bzw. alle Stationen sehr ausgeglichen ausgelastet sind, um verschiedene Szenarien zu simulieren. Die Zielvariable ist eine möglichst geringe Summe an Verspätungen bzw. eine möglichst hohe Scheduling Efficiency.

#### Beispiel


|OrderNo|PartNo|BendingLines|WeldingPoints|PaintTime|DueDate|
|-------|------|------------|-------------|---------|-------|
| 0     | 0    |4           |9            |5        |   344 |
| 0     | 1    |5           |0            |6        |   344 |
| 1     | 0    |7           |0            |0        |    58 |
| 1     | 1    |7           |7            |8        |    58 |
| 2     | 0    |2           |8            |3        |   303 |
| ...   | ...  |...         |...          |...      |   ... |




### Team

* Ege Çimşir
* Jonas Gottal
* Sebastian Silva
* Tobias Rohe
* Viktoria Patapovich





