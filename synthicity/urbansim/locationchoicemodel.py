{% from 'modelspec.py' import IMPORTS, MERGE, SPEC, CALCVAR, TABLE with context %}
{{ IMPORTS() }}
SAMPLE_SIZE=100

{% if template_mode == "estimate" %}
def {{modelname}}_estimate(dset,year=None,show=True):

  assert "{{model}}" == "locationchoicemodel" # should match!
  returnobj = {}
  
  # TEMPLATE configure table
  {{ TABLE(internalname)|indent(2) }}
  # ENDTEMPLATE
  
  {% if est_sample_size -%} 
  # TEMPLATE randomly choose estimatiors
  {{internalname}} = {{internalname}}.loc[np.random.choice({{internalname}}.index, {{est_sample_size}},replace=False)]
  # ENDTEMPLATE
  {% endif -%}
  
  # TEMPLATE specifying alternatives
  alternatives = {{alternatives}}
  # ENDTEMPLATE
  
  {% if merge -%}
  # TEMPLATE merge
  {{- MERGE("alternatives",merge) | indent(2) }}
  # ENDTEMPLATE
  {% endif -%}

  t1 = time.time()

  {% if segment is not defined -%}
  segments = [(None,{{internalname}})]
  {% else -%}
  # TEMPLATE creating segments
  {% for varname in segment -%}
  {% if varname in var_lib -%}
  
  if "{{varname}}" not in {{internalname}}.columns: 
    {{internalname}}["{{varname}}"] = {{CALCVAR(internalname,varname,var_lib)}}
  {% endif -%}
  {% endfor -%}
  segments = {{internalname}}.groupby({{segment}})
  # ENDTEMPLATE
  {% endif  %}
  
  for name, segment in segments:

    name = str(name)
    outname = "{{modelname}}" if name is None else "{{modelname}}_"+name

    global SAMPLE_SIZE
    {% if alt_sample_size -%}
    SAMPLE_SIZE = {{alt_sample_size}}
    {% endif -%}
    sample, alternative_sample, est_params = interaction.mnl_interaction_dataset(
                                        segment,alternatives,SAMPLE_SIZE,chosenalts=segment["{{dep_var}}"])

    print "Estimating parameters for segment = %s, size = %d" % (name, len(segment.index)) 

    # TEMPLATE computing vars
    {{ SPEC("alternative_sample","data",submodel="name") | indent(4) }}
    # ENDTEMPLATE
    if show: print data.describe()

    d = {}
    d['columns'] = fnames = data.columns.tolist()

    data = data.as_matrix()
    if np.amax(data) > 500.0:
      raise Exception("WARNING: the max value in this estimation data is large, it's likely you need to log transform the input")
    fit, results = interaction.estimate(data,est_params,SAMPLE_SIZE)
 
    fnames = interaction.add_fnames(fnames,est_params)
    if show: print misc.resultstotable(fnames,results)
    misc.resultstocsv(fit,fnames,results,outname+"_estimate.csv",tblname=outname)
    
    d['null loglik'] = float(fit[0])
    d['converged loglik'] = float(fit[1])
    d['loglik ratio'] = float(fit[2])
    d['est_results'] = [[float(x) for x in result] for result in results]
    returnobj[name] = d
    
    dset.store_coeff(outname,zip(*results)[0],fnames)

  print "Finished executing in %f seconds" % (time.time()-t1)
  return returnobj

{% else %}
def {{modelname}}_simulate(dset,year=None,show=True):

  returnobj = {}
  t1 = time.time()
  # TEMPLATE configure table
  {{ TABLE(internalname)|indent(2) }}
  # ENDTEMPLATE
  
  # TEMPLATE dependent variable
  depvar = "{{dep_var}}"
  # ENDTEMPLATE

  {% if relocation_rates -%} 
  # TEMPLATE computing relocations
  movers = dset.relocation_rates({{internalname}},{{relocation_rates.rate_table}},"{{relocation_rates.rate_field}}")
  {{internalname}}["{{dep_var}}"].loc[movers] = -1
  # add current unplaced
  movers = {{internalname}}[{{internalname}}["{{dep_var}}"]==-1]
  # ENDTEMPLATE
  {% elif relocation_rate -%}
  # TEMPLATE computing relocations
  movers = {{internalname}}[np.random.sample(len({{internalname}}.index)) < {{relocation_rate}}].index
  print "Count of movers = %d" % len(movers)
  {{internalname}}["{{dep_var}}"].loc[movers] = -1
  # add current unplaced
  movers = {{internalname}}[{{internalname}}["{{dep_var}}"]==-1]
  # ENDTEMPLATE
  {% else -%}
  movers = {{internalname}} # everyone moves
  {% endif %}

  print "Total new agents and movers = %d (out of %d %s)" % (len(movers.index),len({{internalname}}.index),"{{internalname}}")

  # TEMPLATE specifying alternatives
  alternatives = {{alternatives}}
  # ENDTEMPLATE
  
  {% if supply_constraint -%}
  # TEMPLATE computing supply constraint
  vacant_units = {{supply_constraint}}
  {% if demand_amount_scale -%}
  vacant_units /= float({{demand_amount_scale}})
  {% endif -%}
  vacant_units = vacant_units[vacant_units>0].order(ascending=False)
  {% if dontexpandunits -%} 
  alternatives = alternatives.loc[vacant_units.index]
  alternatives["supply"] = vacant_units
  {% else -%}  
  alternatives = alternatives.loc[np.repeat(vacant_units.index,vacant_units.values.astype('int'))].reset_index()
  {% endif -%}
  print "There are %s empty units in %s locations total in the region" % (vacant_units.sum(),len(vacant_units))
  # ENDTEMPLATE
  {% endif -%}

  {% if merge -%}
  # TEMPLATE merge
  {{- MERGE("alternatives",merge) | indent(2) }}
  # ENDTEMPLATE
  {% endif %}

  print "Finished specifying model in %f seconds" % (time.time()-t1)

  t1 = time.time()

  pdf = pd.DataFrame(index=alternatives.index) 
  {% if segment is not defined -%}
  segments = [(None,movers)]
  {% else -%}
  # TEMPLATE creating segments
  {% for varname in segment -%}
  {% if varname in var_lib -%}
  
  if "{{varname}}" not in movers.columns: 
    movers["{{varname}}"] = {{CALCVAR("movers",varname,var_lib)}}
  {% endif -%}
  {% endfor -%}
  segments = movers.groupby({{segment}})
  # ENDTEMPLATE
  {% endif  %}

  for name, segment in segments:

    segment = segment.head(1)

    name = str(name)
    outname = "{{modelname}}" if name is None else "{{modelname}}_"+name
  
    SAMPLE_SIZE = alternatives.index.size # don't sample
    sample, alternative_sample, est_params = \
             interaction.mnl_interaction_dataset(segment,alternatives,SAMPLE_SIZE,chosenalts=None)
    # TEMPLATE computing vars
    {{ SPEC("alternative_sample","data",submodel="name") | indent(4) }}
    # ENDTEMPLATE
    data = data.as_matrix()

    coeff = dset.load_coeff(outname)
    probs = interaction.mnl_simulate(data,coeff,numalts=SAMPLE_SIZE,returnprobs=1)
    pdf['segment%s'%name] = pd.Series(probs.flatten(),index=alternatives.index) 

  print "Finished creating pdf in %f seconds" % (time.time()-t1)
  if len(pdf.columns) and show: print pdf.describe()
  returnobj["{{modelname}}"] = misc.pandasdfsummarytojson(pdf.describe(),ndigits=10)
  pdf.describe().to_csv(os.path.join(misc.output_dir(),"{{modelname}}_simulate.csv"))
    
  {% if save_pdf -%}
  dset.save_tmptbl("{{save_pdf}}",pdf)
  {% endif %}

  {%- if supply_constraint -%}
  t1 = time.time()
  # draw from actual units
  new_homes = pd.Series(np.ones(len(movers.index))*-1,index=movers.index)
  mask = np.zeros(len(alternatives.index),dtype='bool')
  for name, segment in segments:
    name = str(name)
    print "Assigning units to %d agents of segment %s" % (len(segment.index),name)
    p=pdf['segment%s'%name].values
     
    {% if dontexpandunits -%}
    {% if demand_amount -%}
    tmp = segment["{{demand_amount}}"]
    {% if demand_amount_scale -%}
    tmp /= {{demand_amount_scale}}
    {% endif -%}
    for name, subsegment in reversed(list(segment.groupby(tmp.astype('int')))):
      print "Running subsegment with size = %s, num agents = %d" % (name, len(subsegment.index))
      mask,new_homes = dset.choose(p,mask,alternatives,subsegment,new_homes,minsize=int(name))
    {% else -%}
    print "WARNING: you've specified a supply constraint but no demand_amount - all demands will be of value 1"
    {% endif %}
    {% else -%}
    mask,new_homes = dset.choose(p,mask,alternatives,segment,new_homes)
    {% endif %}

  {% if not dontexpandunits -%}
  new_homes = pd.Series(alternatives["{{dep_var}}"].loc[new_homes].values,index=new_homes.index) 
  {% endif %}

  build_cnts = new_homes.value_counts()
  print "Assigned %d agents to %d locations with %d unplaced" % \
                      (new_homes.size,build_cnts.size,build_cnts.get(-1,0))

  # need to go back to the whole dataset
  table = {{output_table if output_table else table_sim if table_sim else table}} 
  table["{{dep_var}}"].loc[new_homes.index] = new_homes.values
  dset.store_attr("{{output_varname}}",year,copy.deepcopy(table["{{dep_var}}"]))
  print "Finished assigning agents in %f seconds" % (time.time()-t1)
  {% endif -%}

  return returnobj

{% endif %}
