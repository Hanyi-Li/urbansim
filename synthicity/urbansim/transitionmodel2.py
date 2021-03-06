{% from 'modelspec.py' import IMPORTS, MERGE, SPEC, TABLE with context %}
{{ IMPORTS() }}
def {{modelname}}_{{template_mode}}(dset,year=None,show=True):
  assert "{{model}}" == "transitionmodel2" # should match!
  returnobj = {}
  t1 = time.time()
  
  # keep original indexes
  if "{{output_varname}}" not in {{table}}.columns: {{table}} = {{table}}.reset_index() 

  # TEMPLATE configure table
  {{ TABLE(internalname)|indent(2) }}
  # ENDTEMPLATE

  # TEMPLATE growth rate
  {% if growth_rate -%}
  newdf = {{internalname}}[np.random.sample(len({{internalname}}.index)) < {{growth_rate}}]
  {% endif -%}
  # ENDTEMPLATE

  # TEMPLATE fields to zero out
  {% for name in zero_out_names -%}
  newdf["{{name}}"] = -1
  {% endfor -%}
  # ENDTEMPLATE

  print "Adding %d rows" % len(newdf.index)
  if show: print newdf.describe()

  # concat and make index unique again
  {{table}} = pd.concat([{{table}},newdf],axis=0).reset_index(drop=True)
  if show: print {{table}}.describe()

  dset.store_attr("{{output_varname}}",year,copy.deepcopy({{table}}.{{output_varname}}))
