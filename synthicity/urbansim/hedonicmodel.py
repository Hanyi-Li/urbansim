{% from 'modelspec.py' import IMPORTS, MERGE, SPEC, TABLE with context %}
{{ IMPORTS() }}
def {{modelname}}_{{template_mode}}(dset,year=None,show=True):

  assert "{{model}}" == "hedonicmodel" # should match!
  returnobj = {}
  t1 = time.time()
  
  # TEMPLATE configure table
  {{ TABLE(internalname)|indent(2) }}
  # ENDTEMPLATE

  {% if merge -%}
  # TEMPLATE merge
  {{- MERGE(internalname,merge) | indent(2) }}
  # ENDTEMPLATE
  {% endif %}

  print "Finished specifying in %f seconds" % (time.time()-t1)
  t1 = time.time()

  {% if not template_mode == "estimate" -%}
  simrents = []
  {% endif -%}
  {% if segment is not defined -%}
  segments = [(None,{{internalname}})]
  {% else -%}
  # TEMPLATE creating segments
  segments = {{internalname}}.groupby({{segment}})
  # ENDTEMPLATE
  {% endif  %}
  
  for name, segment in segments:
    name = str(name)
    outname = "{{modelname}}" if name is None else "{{modelname}}_"+name
    
    # TEMPLATE computing vars
    {{ SPEC("segment","est_data",submodel="name") | indent(4) }}
    # ENDTEMPLATE

    {%- if template_mode == "estimate" %}


    # TEMPLATE dependent variable
    depvar = segment["{{dep_var}}"]
    {% if dep_var_transform is defined -%}
    depvar = depvar.apply({{dep_var_transform}})
    # ENDTEMPLATE
    {% endif %}

    if name: print "Estimating hedonic for %s with %d observations" % (name,len(segment.index))
    if show: print est_data.describe()
    dset.save_tmptbl("EST_DATA",est_data) # in case we want to explore via urbansimd

    model = sm.OLS(depvar,est_data)
    results = model.fit()
    if show: print results.summary()

    misc.resultstocsv((results.rsquared,results.rsquared_adj),est_data.columns,
                        zip(results.params,results.bse,results.tvalues),outname+"_estimate.csv",hedonic=1,
                        tblname=outname)
    d = {}
    d['rsquared'] = results.rsquared
    d['rsquared_adj'] = results.rsquared_adj
    d['columns'] =  est_data.columns.tolist()
    d['est_results'] =  zip(results.params,results.bse,results.tvalues)
    returnobj[name] = d

    dset.store_coeff(outname,results.params.values,results.params.index)
    {% else -%} {# SIMULATE #} 
    
    print "Generating rents on %d %s" % (est_data.shape[0],"{{internalname}}")
    vec = dset.load_coeff(outname)
    vec = np.reshape(vec,(vec.size,1))
    rents = est_data.dot(vec).astype('f4')
    {% if output_transform -%}
    rents = rents.apply({{output_transform}})
    {% endif -%}
    simrents.append(rents[rents.columns[0]])
    returnobj[name] = misc.pandassummarytojson(rents.describe())
    rents.describe().to_csv(os.path.join(misc.output_dir(),"{{modelname}}_simulate.csv"))
    {% endif %}
  
  {% if not template_mode == "estimate" -%}
  simrents = pd.concat(simrents)

  {{output_table}}["{{output_varname}}"] = simrents.reindex({{output_table}}.index)
  dset.store_attr("{{output_varname}}",year,simrents)

  {% endif -%}
  
  print "Finished executing in %f seconds" % (time.time()-t1)
  return returnobj
