
# Search text to translate accross all project
grep -Pr "T\(\".*?\"\)" --include=\*.py . > temp1.txt
grep -Pr "T\(\".*?\"\)" --include=\*.html . >> temp1.txt
grep -Pr "T\('.*?'\)" --include=\*.py . >> temp1.txt
grep -Pr "T\('.*?'\)" --include=\*.html . >> temp1.txt

# Formatting to JSON
perl -pe '{s/(.*)T\((\".*?\")\)(.*)/\2: \2,/g}' temp1.txt > temp2.txt
perl -pe "{s/(.*)T\(('.*?')\)(.*)/\2: \2,/g}" temp2.txt > temp3.txt
# Remove some errors
perl -pe '{s/(\".*?\")\, lazy=False(.*)/\1: \1,/g}' temp3.txt > temp4.txt

# Copy default language file
cp languages/default.py temp_basefile.txt

perl -pe '{s/\ \ \ \ //g}' temp_basefile.txt > basefile.txt

# Remove first and last lines
sed -i '1d' basefile.txt
sed -i '1d' basefile.txt
sed '$d' basefile.txt >> temp4.txt

# Remove duplicates
sort temp4.txt -o temp4.txt
sort temp4.txt | uniq > result.txt
rm temp1.txt temp2.txt temp3.txt temp4.txt basefile.txt temp_basefile.txt

# NEXT STEPS (remove some duplicates caused by '' and "") :
# - copy result.txt inside default.py python list
# - run black python formatter (auto replace '' by "") on default.py
# - copy formatting result in a new file result2.txt 
# - run following command to remove duplicates : "sort result2.txt | uniq > result3.txt"
# - copy result2.txt inside default.py python list
