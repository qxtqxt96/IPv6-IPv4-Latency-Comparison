#! /bin/bash


CONFDIR=./conf/
RESULTDIR=./domain_ips/


urls=($(cat ${CONFDIR}/urls.txt))
nameservers=($(cat ${CONFDIR}/nameservers.txt | grep '[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*' | sort -u))

N=100

ts=$(date '+%s')

for url in ${urls[*]}
do
    for dns_server in ${nameservers[*]}
    do
        { dig -t A +short @$dns_server $url > /tmp/.${url}.${ts}.${dns_server}.txt;\
        dig -t AAAA +short @$dns_server $url >> /tmp/.${url}.${ts}.${dns_server}.txt;} &

        joblist=($(jobs -p))
        while (( ${#joblist[*]} > $N ))
        do
            sleep 0.1
            joblist=($(jobs -p))
        done
    done

    wait

    cat /tmp/.${url}.${ts}.*.txt | sort -u | grep -v ';;' >${RESULTDIR}/${url}
    find /tmp/ -name ".${url}.${ts}.*.txt" | xargs rm -f

done
